
from .interface import load_tx_sequence
from ..coverage import InstCoverage
from ..common.utils import symbolicate_tx_data
from maat import ARCH, contract, MaatEngine, Solver, STOP
from typing import Optional

import os

def replay_inputs(corpus_dir: str, contract_file: str, cov: Optional[InstCoverage] = None) -> InstCoverage:

    # Initialise engine and load contract
    m = MaatEngine(ARCH.EVM)
    m.load(contract_file)

    # Building upon existing coverage?
    if not cov:
        cov = InstCoverage()
    cov.track(m)

    # Run every input from the corpus
    for corpus_file in os.listdir(corpus_dir)[:1]:
        corpus_file = os.path.join(corpus_dir, corpus_file)
        if not corpus_file.endswith('.txt'):
            continue
        print(f"Replaying inputs from {corpus_file}")

        tx = load_tx_sequence(corpus_file)[0]
        contract(m).transaction = tx
        symbolicate_tx_data(m)
        cov.set_input_uid(m, corpus_file)
        # Run
        init_state = m.take_snapshot()
        m.run()
        # Make sure transaction was executed properly
        assert m.info.stop == STOP.EXIT
        m.restore_snapshot(init_state)
  
    return cov
            
def generate_new_inputs(cov: InstCoverage):

    # Keep only interesting bifurcations
    cov.filter_bifurcations()
    cov.sort_bifurcations()

    res = []
    count = len(cov.bifurcations)
    print(f"Trying to solve {count} possible new paths...")

    for i,bif in enumerate(cov.bifurcations):
        print(f"Solving {i+1} of {count} ({round((i/count)*100, 2)}%)")
        s = Solver()

        # Add path constraints in
        for path_constraint in bif.path_constraints:
            s.add(path_constraint)
        # Add constraint to branch to new code
        s.add(bif.alt_target_constraint)

        if s.check():
            model = s.get_model()
            # TODO: so far we can just return the models but eventually
            # we will need to serialize them as proper echidna JSON corpus files.
            # To be implemented after issue #3 is closed.
            res.append(model)

    return res