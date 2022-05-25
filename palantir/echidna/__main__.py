
import argparse
import sys

from .runner import replay_inputs

def main() -> None:
    
    args = parse_arguments()

    # Initialise maat engine
    ins = replay_inputs(args.corpus_dir, args.contract)
    print("ins:", ins)

def parse_arguments() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description = "Concolic fuzzing tool",
        prog=sys.argv[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "corpus_dir",
        type=str,
        help="Echidna corpus directory to replay"
    )
    
    parser.add_argument(
        "contract",
        type=str,
        help="Compiled smart contract to run"
    )

    return parser.parse_args(sys.argv[1:])


if __name__ == "__main__":
    main()
