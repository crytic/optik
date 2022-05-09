from .interface import load_tx_sequence
from maat import *
import sys


def main() -> None:
    corpus_file = sys.argv[1]
    print(load_tx_sequence(corpus_file))


if __name__ == "__main__":
    main()
