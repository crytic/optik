import argparse
import sys
import os
import tempfile

from .runner import replay_inputs, generate_new_inputs, run_echidna_campaign
from .interface import extract_contract_bytecode
from ..coverage import (
    InstCoverage,
    InstIncCoverage,
    InstTxCoverage,
    InstTxSeqCoverage,
    InstSgCoverage,
    PathCoverage,
    RelaxedPathCoverage,
)
from slither.slither import Slither
from ..common.logger import logger, handler
import logging
from typing import List, Set
from ..corpus.generator import (
    EchidnaCorpusGenerator,
    infer_previous_incremental_threshold,
)


def run_hybrid_echidna(args: List[str]) -> None:
    """Main hybrid echidna script"""

    args = parse_arguments(args)
    max_seq_len = args.seq_len
    try:
        deployer = int(args.deployer, 16)
    except:
        logger.error(f"Invalid deployer address: {args.deployer}")
        return

    if args.debug:
        handler.setLevel(logging.DEBUG)

    if args.corpus_dir is None:
        args.corpus_dir = tempfile.TemporaryDirectory(dir=".").name

    coverage_dir = os.path.join(args.corpus_dir, "coverage")

    # Coverage tracker for the whole fuzzing session
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
    if prev_threshold:
        logger.info(
            f"Incremental seeding was already used on this corpus with threshold {prev_threshold}"
        )

    do_incremental_seeding = not args.no_incremental
    if do_incremental_seeding:
        slither = Slither(args.FILES[0])
        gen = EchidnaCorpusGenerator(args.contract, slither)

    # Set of corpus files we have already processed
    seen_files = set()

    iter_cnt = 0
    new_inputs_cnt = 0
    while args.max_iters is None or iter_cnt < args.max_iters:
        iter_cnt += 1

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
                args.seq_len = (
                    1
                    if not prev_threshold
                    else min(prev_threshold, args.incremental_threshold)
                )
            # Update corpus seeding
            elif args.seq_len < max_seq_len:
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

        # Run echidna fuzzing campaign
        logger.info(f"Running echidna campaign #{iter_cnt} ...")
        p = run_echidna_campaign(args)
        # Note: return code is not a reliable error indicator for Echidna
        # so we check stderr to detect potential errors running Echidna
        if p.stderr:
            logger.fatal(f"Echidna failed with exit code {p.returncode}")
            logger.fatal(f"Echidna stderr: \n{p.stderr}")
            return

        logger.debug(f"Echidna stdout: \n{p.stdout}")

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

        # Replay new corpus inputs symbolically
        new_inputs = pull_new_corpus_files(coverage_dir, seen_files)
        if new_inputs:
            logger.info(
                f"Replaying {len(new_inputs)} new inputs symbolically..."
            )
        else:
            logger.info(f"Echidna couldn't find new inputs")
            return
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
    return


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
        else:
            seen_files.add(corpus_file)
            res.append(corpus_file)
    return res


def parse_arguments(args: List[str]) -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Hybrid fuzzer with Echidna & Maat",
        prog=sys.argv[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    def auto_int(x):
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

    parser.add_argument("--debug", action="store_true", help="Print debug logs")

    return parser.parse_args(args)


def main() -> None:
    run_hybrid_echidna(sys.argv[1:])


if __name__ == "__main__":
    main()
