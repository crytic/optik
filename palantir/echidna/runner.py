from .interface import load_tx_sequence
from ..coverage import InstCoverage
from ..common.utils import symbolicate_tx_data
from ..common.world import EVMWorld, WorldMonitor
from ..common.logger import logger
import logging
from maat import ARCH, contract, EVMTransaction, MaatEngine, Solver, STOP
from typing import Optional

import os

logger.setLevel(logging.DEBUG)


class SymbolicateTxData(WorldMonitor):
    def __init__(self):
        super().__init__()

    def on_transaction(self, tx: EVMTransaction) -> None:
        symbolicate_tx_data(self.world.current_engine)


tx_symbolicator = SymbolicateTxData()


def replay_inputs(
    corpus_dir: str, contract_file: str, cov: Optional[InstCoverage] = None
) -> InstCoverage:

    # Building upon existing coverage?
    if not cov:
        cov = InstCoverage()

    # Run every input from the corpus
    logger.info(f"Replaying inputs from corpus: {corpus_dir}")
    for corpus_file_name in os.listdir(corpus_dir):
        corpus_file = os.path.join(corpus_dir, corpus_file_name)
        if not corpus_file.endswith(".txt"):
            continue
        logger.debug(f"Replaying input: {corpus_file_name}")

        tx = load_tx_sequence(corpus_file)[0]
        # TODO(boyan): implement snapshoting in EVMWorld so we don't
        # recreate the whole environment for every input
        world = EVMWorld()
        world.deploy(contract_file, tx.recipient)
        world.attach_monitor(cov, tx.recipient)
        world.attach_monitor(tx_symbolicator)

        # Prepare to run transaction
        world.push_transaction(tx)
        cov.set_input_uid(corpus_file)

        # Run
        assert world.run() == STOP.EXIT

    return cov


def generate_new_inputs(cov: InstCoverage):

    # Keep only interesting bifurcations
    cov.filter_bifurcations()
    cov.sort_bifurcations()

    res = []
    count = len(cov.bifurcations)
    logger.info(f"Trying to solve {count} possible new paths...")

    for i, bif in enumerate(cov.bifurcations):
        logger.info(f"Solving {i+1} of {count} ({round((i/count)*100, 2)}%)")
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
