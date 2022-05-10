from .interface import load_tx_sequence
from ..coverage import InstCoverage
from ..common.utils import symbolicate_tx_data
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
    symbolicate_tx_data(m)

    # Enable code coverage tracking
    cov = InstCoverage()
    cov.track(m)
    # TODO uncomment when supporting MaatEngine.uid
    # cov.set_input_uid(m, corpus_file)

    # Run
    init_state = m.take_snapshot()
    m.run()
    m.restore_snapshot(init_state)


if __name__ == "__main__":
    main()
