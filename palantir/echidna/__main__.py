
import argparse
import sys

from maat import MaatEngine, ARCH

from .runner import replay_inputs

def main() -> None:
    
    args = parse_arguments()

    # Initialise maat engine
    m = MaatEngine(ARCH.EVM)
    ins = replay_inputs(m, args.corpus_dir, args.contract_file)
    print("ins:", ins)

def parse_arguments() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description = "Concolic fuzzing tool",
        prog="palantir-echidna",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--corpus_dir",
        type=str,
        default=".",
        help=""
        )
    
    parser.add_argument(
        "--contract_file"
    )

    return parser.parse_args(sys.argv[1:])


if __name__ == "__main__":
    main()
