from .interface import load_tx_sequence
from ..coverage import InstCoverage
from ..common.utils import symbolicate_tx_data
from maat import ARCH, contract, EVM, MaatEngine, Solver
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
    cov.set_input_uid(m, corpus_file)

    # Run
    init_state = m.take_snapshot()
    m.run()
    m.restore_snapshot(init_state)

    # Get possible new paths
    cov.filter_bifurcations()
    cov.sort_bifurcations()
    for bif in cov.bifurcations:
        s = Solver()
        for path_constraint in bif.path_constraints:
            s.add(path_constraint)
        s.add(bif.alt_target_constraint)
        print("Solving new input...")
        if s.check():
            model = s.get_model()
            print(f"Found new input: {model}")


if __name__ == "__main__":
    main()
