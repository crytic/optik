
from .interface import load_tx_sequence
from ..coverage import InstCoverage
from ..common.utils import symbolicate_tx_data
from maat import MaatEngine, contract, Solver
from typing import Optional

import os


def replay_inputs(m: MaatEngine, corpus_dir: str, contract_file: str, cov: Optional[InstCoverage] = None) -> InstCoverage:

    # Initialise contract
    m.load(contract_file)

    # Building upon existing coverage?
    if not cov:
        cov = InstCoverage()

    # TODO: abstract `coverage` out into a config?
    coverage_dir = os.path.join(os.path.realpath(corpus_dir), "coverage")

    cov.track(m)
    # Load individual input corpora
    for corpus_file in os.listdir(coverage_dir):
        print(f"Loading inputs from {coverage_dir + '/' + corpus_file}")
        corpus_file = os.path.join(coverage_dir, corpus_file)

        if not corpus_file.endswith('.txt'):
            continue

        tx = load_tx_sequence(corpus_file)[0]
        contract(m).transaction = tx
        symbolicate_tx_data(m)

        
        cov.set_input_uid(m, corpus_file)

    # Run
    init_state = m.take_snapshot()
    m.run()
    m.restore_snapshot(init_state)

    # Get possible new paths
    cov.filter_bifurcations()
    cov.sort_bifurcations()

    # Get possible new paths
    new_inputs = find_new_inputs(cov)
        
    return new_inputs
            
def find_new_inputs(cov: InstCoverage):

    paths = []

    count = len(cov.bifurcations)
    print("There are:", count, "to solve...")

    for i,bif in enumerate(cov.bifurcations):
        print(f"Solving {i} of {count} ({round((i/count)*100, 2)}%)")
        s = Solver()

        # add paths in
        for path_constraint in bif.path_constraints:
            s.add(path_constraint)
            
        s.add(bif.alt_target_constraint)

        if s.check():
            model = s.get_model()
            paths.append(model)
    
    return paths