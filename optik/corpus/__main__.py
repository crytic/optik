import argparse
import sys
from typing import List
from slither.slither import Slither
from .generator import EchidnaCorpusGenerator
from ..common.logger import logger
from ..common.exceptions import CorpusException


def run_feed_echidna(arguments: List[str]) -> None:
    """Main corpus generation script"""

    args = parse_arguments(arguments)
    slither = Slither(args.FILE)
    gen = EchidnaCorpusGenerator(args.contract, slither)
    logger.info(f"Getting transaction templates from {args.corpus_dir}...")
    gen.init_func_template_mapping(args.corpus_dir)
    new_inputs_cnt = 0
    try:
        for _ in range(args.depth - 1):
            gen.step()
            new_inputs_cnt += len(gen.current_tx_sequences)
            gen.dump_tx_sequences(args.corpus_dir)
    except CorpusException as e:
        logger.error(f"Error generating new seeds: {str(e)}")

    logger.info(
        f"Generated {new_inputs_cnt} transaction sequences in {args.corpus_dir}"
    )


def parse_arguments(args: List[str]) -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Fuzzer corpus generation",
        prog=sys.argv[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    def auto_pos_int(x: str) -> int:
        res = int(x, 0)
        if res <= 0:
            raise argparse.ArgumentTypeError("Depth must be strictly positive")
        return res

    parser.add_argument("FILE", type=str, help="Solidity file to analyze")

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
        help="Corpus directory with transaction samples for this contract",
        metavar="PATH",
        required=True,
    )

    parser.add_argument(
        "--depth",
        type=auto_pos_int,
        help="Dataflow depth for tx sequence generation. The bigger depth the longer inputs",
        metavar="INTEGER",
        required=True,
    )

    return parser.parse_args(args)


def main() -> None:
    run_feed_echidna(sys.argv[1:])


if __name__ == "__main__":
    main()
