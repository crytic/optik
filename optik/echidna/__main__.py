import argparse
import sys
import os

from .runner import replay_inputs, generate_new_inputs, run_echidna_campaign
from .interface import extract_contract_bytecode
from ..coverage import InstCoverage
from ..common.logger import logger


def main() -> None:
    args = parse_arguments()

    # Run echidna fuzzing campaign
    p = run_echidna_campaign(args)
    if p.returncode != 0:
        logger.fatal(f"Echidna failed with exit code {p.returncode}")
        return

    # Extract contract bytecode
    # TODO: this must run only once after the first fuzzing campaign
    # TODO: this should return a list of contracts if multiple contracts
    # TODO: is it OK to assume crytic-export is always located in the
    #       current working directory?
    contract_file = extract_contract_bytecode("./crytic-export")

    # Replay echidna corpus
    cov = InstCoverage()  # TODO: coverage must be created only once
    cov = replay_inputs(
        os.path.join(args.corpus_dir, "coverage"), contract_file, cov
    )

    # Find inputs to reach new code
    new_inputs_cnt = generate_new_inputs(cov)
    if new_inputs_cnt > 0:
        logger.info(f"Generated {new_inputs_cnt} new inputs")
    else:
        logger.info(f"Couldn't generate more inputs")
        return


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

    return parser.parse_args(sys.argv[1:])


if __name__ == "__main__":
    main()
