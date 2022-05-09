from .interface import load_tx_sequence
from maat import ARCH, contract, EVM, MaatEngine
import sys


def main() -> None:
    corpus_file = sys.argv[1]
    contract_file = sys.argv[2]
    # Load echidna transaction from corpus and initialize engine with
    # the contract and transaction
    tx = load_tx_sequence(corpus_file)[0]
    m = MaatEngine(ARCH.EVM)
    m.load(contract_file)
    contract(m).transaction = tx
    # Run
    m.run()


if __name__ == "__main__":
    main()
