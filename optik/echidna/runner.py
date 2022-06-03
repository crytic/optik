from .interface import load_tx_sequence, store_new_tx_sequence
from ..coverage import InstCoverage
from ..common.utils import symbolicate_tx_data
from ..common.world import EVMWorld, WorldMonitor
from ..common.logger import logger
import argparse
import subprocess
import logging
from maat import ARCH, contract, EVMTransaction, MaatEngine, Solver, STOP
from typing import List, Optional

import os

logger.setLevel(logging.DEBUG)


class SymbolicateTxData(WorldMonitor):
    def __init__(self):
        super().__init__()

    def on_transaction(self, tx: EVMTransaction) -> None:
        symbolicate_tx_data(self.world.current_engine)


tx_symbolicator = SymbolicateTxData()


def replay_inputs(
    corpus_files: List[str],
    contract_file: str,
    cov: Optional[InstCoverage] = None,
) -> InstCoverage:

    # Building upon existing coverage?
    if not cov:
        cov = InstCoverage()

    # Run every input from the corpus
    for corpus_file in corpus_files:
        logger.debug(f"Replaying input: {os.path.basename(corpus_file)}")

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


def generate_new_inputs(cov: InstCoverage) -> int:
    """Generate new inputs to increase code coverage, base on
    existing coverage

    :param cov: coverage data
    :return: number of new inputs found
    """

    # Keep only interesting bifurcations
    cov.filter_bifurcations()
    cov.sort_bifurcations()

    res = []
    # Count number of "unique" bifurcations, in the sense that
    # two bifurcations to the same target are considered the same,
    # even with different states and path constraints...
    unique_targets = set()
    for bif in cov.bifurcations:
        if bif.alt_target not in unique_targets:
            unique_targets.add(bif.alt_target)
    count = len(cov.bifurcations)
    logger.info(
        f"Solving potential new paths... ({count} total, {len(unique_targets)} unique)"
    )
    success_cnt = 0
    for i, bif in enumerate(cov.bifurcations):
        # Don't solve the same branch target if it was solved already
        if bif.alt_target not in unique_targets:
            continue

        logger.info(f"Solving {i+1} of {count} ({round((i/count)*100, 2)}%)")
        s = Solver()

        # Add path constraints in
        for path_constraint in bif.path_constraints:
            s.add(path_constraint)
        # Add constraint to branch to new code
        s.add(bif.alt_target_constraint)

        if s.check():
            success_cnt += 1
            unique_targets.remove(bif.alt_target)
            model = s.get_model()
            # Serialize the new input discovered
            store_new_tx_sequence(bif.input_uid, model)

    return success_cnt


def run_echidna_campaign(
    args: argparse.Namespace,
) -> subprocess.CompletedProcess:
    """Run an echidna fuzzing campaign

    :param args: arguments to pass to echidna
    :return: the exit value returned by invoking `echidna-test`
    """
    # Build back echidna command line
    cmdline = ["echidna-test"]
    cmdline += args.FILES
    for arg, val in args.__dict__.items():
        # Ignore Optik specific arguments
        if arg not in ["FILES", "max_iters", "debug"] and not val is None:
            cmdline += [f"--{arg.replace('_', '-')}", str(val)]
    logger.debug(f"Echidna invocation cmdline: {' '.join(cmdline)}")
    # Run echidna
    echidna_process = subprocess.run(
        cmdline,
        # TODO(boyan): not piping stdout would allow to display the echidna
        # interface while it runs, but we have to find a way to automatically
        # terminate it with Ctrl+C or Esc once it finishes, otherwise it just
        # hangs and the script can't continue
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    return echidna_process
