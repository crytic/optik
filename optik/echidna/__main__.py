import argparse
import logging
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Set, NoReturn

from slither.exceptions import SlitherError
from slither.slither import Slither

from optik.common.exceptions import GenericException
from .display import (
    display,
    start_display,
    stop_display,
)
from .interface import extract_contract_bytecode, extract_cases_from_json_output
from .runner import replay_inputs, generate_new_inputs, run_echidna_campaign
from ..common.exceptions import ArgumentParsingError, InitializationError
from ..common.logger import (
    logger,
    disable_logging,
    init_logging,
    set_logging_level,
)
from ..common.util import count_files_in_dir
from ..corpus.generator import (
    EchidnaCorpusGenerator,
    infer_previous_incremental_threshold,
)
from ..coverage import (
    InstCoverage,
    InstIncCoverage,
    InstTxCoverage,
    InstTxSeqCoverage,
    InstSgCoverage,
    PathCoverage,
    RelaxedPathCoverage,
    Coverage,
)


def handle_argparse_error(err: ArgumentParsingError) -> None:
    print(f"error: {err.msg}")
    print(err.help_str)


@dataclass(frozen=False)
class FuzzingResult:
    cases_found_cnt: int
    corpus_dir: Optional[str]


def run_hybrid_echidna(arguments: List[str]) -> None:
    """Main hybrid echidna script

    :param args: list of command line arguments
    """
    global glob_fuzzing_result

    # Parse arguments
    try:
        args = parse_arguments(arguments)
    except ArgumentParsingError as e:
        if display.active:
            raise e
        handle_argparse_error(e)
        return

    max_seq_len = args.seq_len
    try:
        deployer = int(args.deployer, 16)
    except ValueError:
        logger.error(f"Invalid deployer address: {args.deployer}")
        return

    display.sym_solver_timeout = args.solver_timeout

    # Logging stream
    if args.logs:
        if args.logs == "stdout" and not args.no_display:
            raise InitializationError(
                "Cannot write logs to stdout while terminal display is enabled. Consider disabling it with '--no-display'"
            )
        init_logging(args.logs)
    else:
        disable_logging()
    if args.debug:
        set_logging_level(logging.DEBUG)

    # Corpus and coverage directories
    if args.corpus_dir is None:
        args.corpus_dir = tempfile.TemporaryDirectory(dir=".").name
    coverage_dir = os.path.join(args.corpus_dir, "coverage")
    glob_fuzzing_result = FuzzingResult(0, args.corpus_dir)

    # Coverage tracker for the whole fuzzing session
    cov: Coverage
    if args.cov_mode == "inst":
        cov = InstCoverage()
    elif args.cov_mode == "inst-tx":
        cov = InstTxCoverage()
    elif args.cov_mode == "path":
        cov = PathCoverage()
    elif args.cov_mode == "path-relaxed":
        cov = RelaxedPathCoverage()
    elif args.cov_mode == "inst-sg":
        cov = InstSgCoverage()
    elif args.cov_mode == "inst-inc":
        cov = InstIncCoverage()
    elif args.cov_mode == "inst-tx-seq":
        cov = InstTxSeqCoverage(args.incremental_threshold)
    else:
        raise GenericException(f"Unsupported coverage mode: {args.cov_mode}")

    # Incremental seeding with feed-echidna
    prev_threshold: Optional[int] = infer_previous_incremental_threshold(
        coverage_dir
    )
    assert prev_threshold is not None
    if prev_threshold:
        logger.info(
            f"Incremental seeding was already used on this corpus with threshold {prev_threshold}"
        )

    do_incremental_seeding = not args.no_incremental
    if do_incremental_seeding:
        slither = Slither(args.FILES[0])
        gen = EchidnaCorpusGenerator(args.contract, slither)

    # Set of corpus files we have already processed
    seen_files: Set[str] = set()

    # Main fuzzing+symexec loop
    iter_cnt = 0
    while args.max_iters is None or iter_cnt < args.max_iters:
        iter_cnt += 1
        display.iteration = iter_cnt  # terminal display

        # If incremental seeding, start with low seq_len and
        # manually increment it at each step
        new_seeds_cnt = 0
        if do_incremental_seeding:
            if iter_cnt == 1:
                # FIXME: No corpus generation at first iteration because the corpus
                # generator needs real corpus files to use as templates for
                # generating arbitrary tx sequences in new corpus files...
                # This would not be necessary if we had a python API
                # to generate JSON echidna inputs

                # If we detected previous incremental seeding, start the seq_len
                # where we stopped last time (or at the current threshold if it's
                # smaller than the previous one). If no previous seeding, start
                # at 1
                if not prev_threshold:
                    args.seq_len = 1
                else:
                    args.seq_len = min(
                        prev_threshold, args.incremental_threshold
                    )
                    gen.step(args.seq_len - 1)
                    gen.init_func_template_mapping(coverage_dir)

            # Update corpus seeding
            if (iter_cnt > 1 and args.seq_len < max_seq_len) or (
                iter_cnt == 1 and prev_threshold
            ):
                # Incremental seeding strategy
                if args.seq_len < args.incremental_threshold:
                    args.seq_len += 1
                    gen.step()
                    new_seeds_cnt = len(gen.current_tx_sequences)
                    if new_seeds_cnt:
                        logger.info(
                            f"Seeding corpus with {new_seeds_cnt} new sequences from dataflow analysis"
                        )
                        gen.dump_tx_sequences(coverage_dir)
                # Quadratic seq_len increase
                else:
                    new_seeds_cnt = 0
                    args.seq_len = min(max_seq_len, args.seq_len * 2)

        # terminal display
        if (
            do_incremental_seeding
            and args.seq_len <= args.incremental_threshold
        ):
            display.mode = (
                f"incremental ({args.seq_len}/{args.incremental_threshold})"
            )
        else:
            display.mode = "normal"  # termial display
        display.corpus_size = count_files_in_dir(coverage_dir)

        # Run echidna fuzzing campaign
        logger.info(f"Running echidna campaign #{iter_cnt} ...")
        start_time = datetime.now()
        p = run_echidna_campaign(args)
        display.fuzz_total_time += int(
            (datetime.now() - start_time).total_seconds() * 1000
        )
        # Note: return code is not a reliable error indicator for Echidna
        # so we check stderr to detect potential errors running Echidna
        if p.stderr:
            logger.fatal(f"Echidna failed with exit code {p.returncode}")
            logger.fatal(f"Echidna stderr: \n{p.stderr}")
            raise GenericException("Echidna failed")

        logger.debug(f"Echidna stdout: \n{p.stdout}")

        # Display cases in terminal
        display.res_cases = extract_cases_from_json_output(p.stdout)
        glob_fuzzing_result.cases_found_cnt = len(display.res_cases)

        # Extract contract bytecodes in separate files for Maat. This is done
        # only once after the first fuzzing campaign
        if iter_cnt == 1:
            # TODO(boyan): is it OK to assume crytic-export is always located in the
            #       current working directory?
            contract_file = extract_contract_bytecode(
                "./crytic-export", args.contract
            )
            if not contract_file:
                logger.fatal("Failed to extract contract bytecode")
                return

            # Initialize corpus generator
            if do_incremental_seeding:
                # TODO(boyan): catch errors
                gen.init_func_template_mapping(coverage_dir)

        # Get new inputs
        new_inputs = pull_new_corpus_files(coverage_dir, seen_files)
        if new_inputs:
            logger.info(
                f"Replaying {len(new_inputs)} new inputs symbolically..."
            )
        else:
            logger.info(f"Echidna couldn't find new inputs")
            break

        # Terminal display
        new_echidna_inputs_cnt = len(
            [
                f
                for f in new_inputs
                if not os.path.basename(f).startswith("optik")
            ]
        )
        display.fuzz_total_cases_cnt += new_echidna_inputs_cnt
        display.fuzz_last_cases_cnt = new_echidna_inputs_cnt
        # Replay new corpus inputs symbolically
        cov.bifurcations = []
        replay_inputs(new_inputs, contract_file, deployer, cov)

        # Find inputs to reach new code
        new_inputs_cnt, timeout_cnt = generate_new_inputs(cov, args)
        if timeout_cnt > 0:
            logger.warning(f"Timed out on {timeout_cnt} cases")
        if new_inputs_cnt > 0:
            logger.info(f"Generated {new_inputs_cnt} new inputs")
        else:
            logger.info(f"Couldn't generate more inputs")

        # If corpus generator didn't have more interesting seeds
        # and no new input, we finish here
        if (
            new_inputs_cnt == 0
            and new_seeds_cnt == 0
            and args.seq_len >= max_seq_len
        ):
            break

    logger.info(f"Corpus and coverage info written in {args.corpus_dir}")


def run_hybrid_echidna_with_display(args: List[str]) -> None:
    """Run hybrid-echidna with terminal display enabled"""
    exc = None
    err_msg = None
    argparse_err = None
    # Start terminal display
    start_display()
    try:
        run_hybrid_echidna(args)
        # Indicate that hybrid echidna finished and
        # wait for user to manually close display
        display.notify_finished()
        while True:
            time.sleep(0.2)
    # Handle many errors to gracefully stop terminal display
    except ArgumentParsingError as e:
        argparse_err = e
    except InitializationError as e:
        err_msg = str(e)
    except (Exception, SlitherError) as e:
        exc = e
    except KeyboardInterrupt:
        pass
    # Close terminal display and reset terminal settings
    stop_display()  # Waits for display threads to exit gracefully
    # Display thread terminated, now handle pending errors or exceptions
    if err_msg:
        logger.error(err_msg)
    if argparse_err:
        handle_argparse_error(argparse_err)
    if exc:
        raise exc


def pull_new_corpus_files(cov_dir: str, seen_files: Set[str]) -> List[str]:
    """Return files in 'cov_dir' that aren't present in 'seen_files'.
    Before returning, 'seen_files' is updated to contain the list of new files
    that the function returns
    """
    res = []
    for corpus_file_name in os.listdir(cov_dir):
        corpus_file = str(os.path.join(cov_dir, corpus_file_name))
        if not corpus_file.endswith(".txt") or corpus_file in seen_files:
            continue
        seen_files.add(corpus_file)
        res.append(corpus_file)
    return res


def parse_arguments(args: List[str]) -> argparse.Namespace:
    class ArgParser(argparse.ArgumentParser):
        """Custom argument parser that doesn't exit on invalid arguments but
        raises a custom exception for Optik to handle"""

        def error(self, message: str) -> NoReturn:
            """Override default behaviour on invalid arguments"""
            raise ArgumentParsingError(msg=message, help_str=self.format_help())

    parser = ArgParser(
        description="Hybrid fuzzer with Echidna & Maat",
        prog=sys.argv[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    def auto_int(x: str) -> int:
        return int(x, 0)

    # Echidna arguments
    parser.add_argument(
        "FILES", type=str, nargs="*", help="Solidity files to analyze"
    )

    parser.add_argument(
        "--contract",
        type=str,
        help="Contract to analyze",
        metavar="CONTRACT",
        required=True,
    )

    parser.add_argument(
        "--corpus-dir",
        type=str,
        help="Directory to save and load corpus and coverage data",
        metavar="PATH",
        default=None,
    )

    parser.add_argument(
        "--test-mode",
        type=str,
        help="Test mode to use",
        choices=[
            "property",
            "assertion",
            "dapptest",
            "optimization",
            "overflow",
            "exploration",
        ],
        default="assertion",
        # metavar="MODE",
    )

    parser.add_argument(
        "--seq-len",
        type=int,
        help="Maximal length for sequences of transactions to generate during testing. If '--no-incremental' is used, all sequences will have exactly this length",
        default=10,
        metavar="INTEGER",
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Config file (command-line arguments override config options)",
        metavar="FILE",
    )

    parser.add_argument(
        "--test-limit",
        type=int,
        help="Number of sequences of transactions to generate",
        default=50000,
        metavar="INTEGER",
    )

    parser.add_argument(
        "--contract-addr",
        type=str,
        help="Address to deploy the contract to test (hex)",
        default="00A329C0648769A73AFAC7F9381E08FB43DBEA72",
        metavar="ADDRESS",
    )

    parser.add_argument(
        "--deployer",
        type=str,
        help="Address of the deployer of the contract to test (hex)",
        default="30000",
        metavar="ADDRESS",
    )

    parser.add_argument(
        "--sender",
        type=str,
        nargs="*",
        default=["10000", "20000", "30000"],
        help="Addresses to use for the transactions sent during testing (hex)",
        metavar="ADDRESSES",
    )

    parser.add_argument(
        "--seed",
        type=auto_int,
        help="Run with a specific seed",
        metavar="INTEGER",
    )

    # Optik arguments
    parser.add_argument(
        "--max-iters",
        type=int,
        help="Number of fuzzing campaigns to run. If unspecified, run until symbolic execution can't find new inputs",
        default=None,
        metavar="INTEGER",
    )

    parser.add_argument(
        "--cov-mode",
        type=str,
        help="Coverage mode to use",
        choices=[
            "inst",
            "inst-tx",
            "path",
            "path-relaxed",
            "inst-sg",
            "inst-inc",
            "inst-tx-seq",
        ],
        default="inst-tx-seq",
        # metavar="MODE",
    )

    parser.add_argument(
        "--solver-timeout",
        type=int,
        help="Maximum solving time (in ms) to spend per potential new input",
        default=None,
        metavar="MILLISECONDS",
    )

    parser.add_argument(
        "--no-incremental",
        action="store_true",
        help="Disable incremental corpus seeding with 'feed-echidna' and only generate transaction sequences of length '--seq-len'",
    )

    parser.add_argument(
        "--incremental-threshold",
        type=int,
        help="The maximal input sequence length up to which to use the incremental corpus seeding strategy",
        default=5,
        metavar="INTEGER",
    )

    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logs"
    )

    parser.add_argument(
        "--logs",
        type=str,
        help="File where to write the logs. Use 'stdout' to print logs to standard output",
        default=None,
        metavar="PATH",
    )

    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Disable the beautiful terminal display",
    )

    return parser.parse_args(args)


# We use a global for the fuzzing result because we need to
# print the output corpus directory to the user no matter
# whether graphical display was enabled and whether we
# exited normally of from an interrupt
glob_fuzzing_result: Optional[FuzzingResult] = None


def main() -> None:
    func = (
        run_hybrid_echidna
        if "--no-display" in sys.argv
        else run_hybrid_echidna_with_display
    )
    func(sys.argv[1:])
    # Print result and exit
    if glob_fuzzing_result:
        print(f"{glob_fuzzing_result.cases_found_cnt} cases found")
        print(
            f"Corpus and coverage info written in {glob_fuzzing_result.corpus_dir}"
        )


if __name__ == "__main__":
    main()
