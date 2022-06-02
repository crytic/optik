import argparse
import sys
import os

from .runner import replay_inputs, generate_new_inputs, run_echidna_campaign
from .interface import extract_contract_bytecode
from ..coverage import InstCoverage
from ..common.logger import logger, handler
import logging
from typing import List, Set


def main() -> None:
    args = parse_arguments()

    if args.debug:
        handler.setLevel(logging.DEBUG)
    coverage_dir = os.path.join(args.corpus_dir, "coverage")

    # Coverage tracker for the whole fuzzing session
    cov = InstCoverage()
    # Set of corpus files we have already processed
    seen_files = set()

    iter_cnt = 0
    while args.max_iters is None or iter_cnt < args.max_iters:
        iter_cnt += 1

        # Run echidna fuzzing campaign
        logger.info(f"Running echidna campaign #{iter_cnt} ...")
        p = run_echidna_campaign(args)
        if p.returncode != 0:
            logger.fatal(f"Echidna failed with exit code {p.returncode}")
            return

        # Extract contract bytecodes in separate files for Maat. This is done
        # only once after the first fuzzing campaign
        if iter_cnt == 1:
            # TODO(boyan): this should return a list of contracts if multiple contracts
            # TODO(boyan): is it OK to assume crytic-export is always located in the
            #       current working directory?
            contract_file = extract_contract_bytecode("./crytic-export")

        # Replay new corpus inputs symbolically
        new_inputs = pull_new_corpus_files(coverage_dir, seen_files)
        if new_inputs:
            logger.info(
                f"Echidna found {len(new_inputs)} new inputs. Replaying them symbolically..."
            )
        else:
            logger.info(f"Echidna couldn't find new inputs")
            return
        cov = replay_inputs(new_inputs, contract_file, cov)

        # Find inputs to reach new code
        new_inputs_cnt = generate_new_inputs(cov)
        if new_inputs_cnt > 0:
            logger.info(f"Generated {new_inputs_cnt} new inputs")
        else:
            logger.info(f"Couldn't generate more inputs")
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


def parse_arguments() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Hybrid fuzzer with Echidna & Maat",
        prog=sys.argv[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Echidna arguments
    parser.add_argument(
        "FILES", type=str, nargs="*", help="Solidity files to analyze"
    )

    parser.add_argument(
        "--corpus-dir",
        type=str,
        help="Directory to save and load corpus and coverage data",
        metavar="PATH",
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
        metavar="MODE",
    )

    parser.add_argument(
        "--seq-len",
        type=int,
        help="Number of transactions to generate during testing",
        default=100,
        metavar="LEN",
    )

    # Optik arguments
    parser.add_argument(
        "--max-iters",
        type=int,
        help="Number of fuzzing campaigns to run. If unspecified, run until symbolic execution can't find new inputs",
        default=None,
        metavar="ITERATIONS",
    )

    parser.add_argument("--debug", action="store_true", help="Print debug logs")

    return parser.parse_args(sys.argv[1:])


if __name__ == "__main__":
    main()
