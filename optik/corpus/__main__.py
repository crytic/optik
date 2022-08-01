import argparse
import sys

from optik.corpus.generator import CorpusGenerator
from slither.slither import Slither
from typing import List


def run_feed_echidna(args: List[str]) -> None:
    """Main corpus generation script"""

    args = parse_arguments(args)
    slither = Slither(args.FILE)
    gen = CorpusGenerator(args.contract, slither)
    gen.init_tx_sequences()
    gen.inc_depth()
    gen.inc_depth()
    print(gen)


def parse_arguments(args: List[str]) -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Fuzzer corpus generation",
        prog=sys.argv[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("FILE", type=str, help="Solidity file to analyze")

    parser.add_argument(
        "--contract",
        type=str,
        help="Contract to analyze",
        metavar="CONTRACT",
        required=True,
    )

    return parser.parse_args(args)


def main() -> None:
    run_feed_echidna(sys.argv[1:])


if __name__ == "__main__":
    main()
