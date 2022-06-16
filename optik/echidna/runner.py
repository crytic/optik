from .interface import load_tx_sequence, store_new_tx_sequence
from ..coverage import Coverage
from ..common.world import EVMWorld, WorldMonitor
from ..common.logger import logger
import argparse
import subprocess
import logging
from maat import ARCH, contract, EVMTransaction, MaatEngine, Solver, STOP
from typing import List, Optional
import os


def replay_inputs(
    corpus_files: List[str],
    contract_file: str,
    contract_deployer: int,
    cov: Coverage,
) -> None:

    # Run every input from the corpus
    for corpus_file in corpus_files:
        logger.debug(f"Replaying input: {os.path.basename(corpus_file)}")

        tx_seq = load_tx_sequence(corpus_file)
        # TODO(boyan): implement snapshoting in EVMWorld so we don't
        # recreate the whole environment for every input
        world = EVMWorld()
        contract_addr = tx_seq[0].tx.recipient
        world.deploy(contract_file, contract_addr, contract_deployer)
        world.attach_monitor(cov, contract_addr)

        # Prepare to run transaction
        world.push_transactions(tx_seq)
        cov.set_input_uid(corpus_file)

        # Run
        assert world.run() == STOP.EXIT

    return cov


def generate_new_inputs(cov: Coverage) -> int:
    """Generate new inputs to increase code coverage, base on
    existing coverage

    :param cov: coverage data
    :return: number of new inputs found
    """

    # Keep only interesting bifurcations
    cov.filter_bifurcations()
    cov.sort_bifurcations()

    res = []
    # Only keep unique bifurcations. Unique means that they have the
    # same target and occurred during the same transaction number in the
    # input sequence
    unique_bifurcations = set(cov.bifurcations)
    count = len(cov.bifurcations)
    logger.info(
        f"Solving potential new paths... ({count} total, {len(unique_bifurcations)} unique)"
    )
    success_cnt = 0
    for i, bif in enumerate(cov.bifurcations):
        # Don't solve identical bifurcations if one was solved already
        if bif not in unique_bifurcations:
            continue

        logger.info(f"Solving {i+1} of {count} ({round((i/count)*100, 2)}%)")
        s = Solver()

        # Add path constraints in
        for path_constraint in bif.path_constraints:
            s.add(path_constraint)
        # Add constraint to branch to new code
        logger.debug(
            f"Solving alt target constraint: {bif.alt_target_constraint}"
        )
        s.add(bif.alt_target_constraint)

        if s.check():
            success_cnt += 1
            unique_bifurcations.remove(bif)
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
    # Add tx sender(s)
    if args.sender:
        for a in args.sender:
            cmdline += ["--sender", str(a)]
    for arg, val in args.__dict__.items():
        # Ignore Optik specific arguments
        if (
            arg not in ["FILES", "max_iters", "debug", "cov_mode", "sender"]
            and not val is None
        ):
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
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return echidna_process
