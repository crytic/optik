import argparse
import json
import os
import subprocess
from datetime import datetime
from typing import List, Optional, Tuple

from maat import (
    Cst,
    EVMTransaction,
    Solver,
    STOP,
    VarContext,
)

from .display import display
from .interface import load_tx_sequence, store_new_tx_sequence
from ..common.logger import logger
from ..common.world import AbstractTx, EVMWorld
from ..coverage import Coverage
from ..common.exceptions import EchidnaException, WorldException


# TODO(boyan): pass contract bytecode instead of extracting to file
def replay_inputs(
    corpus_files: List[str],
    contract_file: str,
    contract_deployer: int,
    cov: Coverage,
    echidna_init_file: Optional[str],
) -> None:

    display.reset_current_task()
    display.current_task_line_1 = "Replaying cases symbolically..."

    # Run every input from the corpus
    for i, corpus_file in enumerate(corpus_files):
        logger.debug(f"Replaying input: {os.path.basename(corpus_file)}")
        display.current_task_line_2 = (
            i + 1,
            len(corpus_files),
        )

        tx_seq = load_tx_sequence(corpus_file)
        # TODO(boyan): implement snapshoting in EVMWorld so we don't
        # recreate the whole environment for every input
        # WARNING: if we end up keeping the same EVMWorld, it will mess with
        # some of the Coverage classes that rely on on_attach(). We'll probably
        # have to detach() and re-attach() them
        world = EVMWorld()
        if echidna_init_file:
            init_world(world, echidna_init_file)

        contract_addr = tx_seq[0].tx.recipient
        # Push initial transaction that initialises the target contract
        world.push_transaction(
            AbstractTx(
                EVMTransaction(
                    Cst(160, contract_deployer),  # origin
                    Cst(160, contract_deployer),  # sender
                    contract_addr,  # recipient
                    Cst(256, 0),  # value
                    [],  # data
                    Cst(256, 50),  # gas price
                    Cst(256, 123456),  # gas limit
                ),
                Cst(256, 0),  # block num inc
                Cst(256, 0),  # block ts inc
                VarContext(),
            )
        )
        world.deploy(
            contract_file,
            contract_addr,
            contract_deployer,
            run_init_bytecode=False,
        )
        world.attach_monitor(cov, contract_addr, tx_seq=tx_seq)

        # Prepare to run transaction
        world.push_transactions(tx_seq)
        cov.set_input_uid(corpus_file)

        # Run and ensure the execution terminated properly
        status = world.run()
        if status in [STOP.FATAL, STOP.ERROR]:
            raise WorldException("Engine stopped because of an error")
        elif status == STOP.HOOK:
            raise WorldException(
                "Engine stopped by an event hook before the end of transaction"
            )
        elif status == STOP.NONE:
            raise WorldException(
                "Engine stopped before the end of transaction for an unknown reason"
            )
        elif status != STOP.EXIT:
            raise WorldException(f"Unexpected engine status: {status}")

    return cov


def init_world(world: EVMWorld, init_file: str) -> None:
    """Setup contracts and EOAs in an EVMWorld according to
    an Echidna state initialisation file"""
    with open(init_file, "r") as f:
        data = json.loads(f.read())
        for event in data:
            if event["event"] == "ContractCreated":
                bytecode = bytes.fromhex(event["data"][2:])
                world.deploy(
                    "",  # No file, bytecode is in the tx data
                    int(event["contract_address"], 16),
                    int(event["from"], 16),
                    args=[bytecode],
                    run_init_bytecode=True,
                )
            elif event["event"] == "AccountCreated":
                pass
            elif event["event"] == "FunctionCall":
                sender = Cst(160, int(event["from"], 16))
                data = bytes.fromhex(event["data"][2:])
                tx = EVMTransaction(
                    sender,  # origin
                    sender,  # sender
                    int(event["to"], 16),  # recipient
                    Cst(256, event["value"][2:], 16),  # value
                    [Cst(8, x) for x in data],  # data
                    Cst(256, int(event["gas_price"], 16)),  # gas price
                    Cst(256, int(event["gas_used"], 16) * 2),  # gas_limit
                )
                world.push_transaction(
                    AbstractTx(
                        tx,
                        Cst(256, 0),
                        Cst(256, 0),
                        VarContext(),
                    )
                )
                status = world.run()
                if status != STOP.EXIT:
                    raise WorldException(
                        f"Failed to properly execute initialisation transaction: {event}"
                    )
                assert not world.has_pending_transactions
            else:
                raise EchidnaException(f"Unsupported event: {event['event']}")


def generate_new_inputs(
    cov: Coverage, args: argparse.Namespace, solve_duplicates: bool = False
) -> Tuple[int, int]:
    """Generate new inputs to increase code coverage, base on
    existing coverage

    :param cov: coverage data
    :param args: echidna arguments. If the new inputs contain particular
    'sender' values for transactions, those are included in the echidna
    list of possible senders
    :param solve_duplicates: forces to generate inputs even for similar bifurcations
    :return: tuple: (number of new inputs found, number of solver timeouts)
    """

    def _add_new_senders(ctx: VarContext, args: argparse.Namespace) -> None:
        for var in ctx.contained_vars():
            if var.endswith("_sender"):
                sender = f"{ctx.get(var):X}"
                if not sender in args.sender:
                    logger.warning(
                        f"Automatically adding new tx sender address: {sender}"
                    )
                    args.sender.append(sender)

    # Keep only interesting bifurcations
    cov.filter_bifurcations()
    cov.sort_bifurcations()

    timeout_cnt = 0
    # Only keep unique bifurcations. Unique means that they have the
    # same target and occurred during the same transaction number in the
    # input sequence
    unique_bifurcations = set(cov.bifurcations)
    count = len(cov.bifurcations)
    logger.info(
        f"Solving potential new paths... ({count} total, {len(unique_bifurcations)} unique)"
    )
    # Terminal display
    display.reset_current_task()
    display.current_task_line_1 = f"Solving new cases... ({count} total, {len(unique_bifurcations)} unique)"
    success_cnt = 0
    for i, bif in enumerate(cov.bifurcations):
        display.current_task_line_2 = (i + 1, count)  # Terminal display

        # Don't solve identical bifurcations if one was solved already
        # and if it's not a custom corpus seed. For custom corpus seeds we
        # still want to solve all bifurcations because all of them should
        # be "meaningfull"
        if bif not in unique_bifurcations and not solve_duplicates:
            continue

        logger.info(f"Solving {i+1} of {count} ({round((i/count)*100, 2)}%)")
        s = Solver()
        if args.solver_timeout:
            s.timeout = args.solver_timeout

        # Add path constraints in
        for path_constraint in bif.path_constraints:
            s.add(path_constraint)
        # Add constraint to branch to new code
        logger.debug(
            f"Solving alt target constraint: {bif.alt_target_constraint}"
        )
        s.add(bif.alt_target_constraint)

        start_time = datetime.now()
        solved = s.check()
        display.update_solving_time(
            int((datetime.now() - start_time).total_seconds() * 1000)
        )
        if solved:
            success_cnt += 1
            if bif in unique_bifurcations:
                unique_bifurcations.remove(bif)
            model = s.get_model()
            # Serialize the new input discovered
            store_new_tx_sequence(bif.input_uid, model)
            _add_new_senders(model, args)
            # Terminal display
            display.sym_total_inputs_solved += 1
        elif s.did_time_out:
            timeout_cnt += 1
            # Terminal display
            display.sym_total_solver_timeouts += 1

        # Terminal display
        display.update_avg_path_constraints(len(bif.path_constraints) + 1)

    return (
        success_cnt,
        timeout_cnt,
    )


def run_echidna_campaign(
    args: argparse.Namespace,
) -> subprocess.CompletedProcess:
    """Run an echidna fuzzing campaign

    :param args: arguments to pass to echidna
    :return: the exit value returned by invoking `echidna`
    """
    # Show for how long echidna runs in terminal display
    display.start_echidna_task_timer()

    # Build back echidna command line
    cmdline = ["echidna"]
    cmdline += args.FILES
    # Add tx sender(s)
    if args.sender:
        for a in args.sender:
            cmdline += ["--sender", a]
    for arg, val in args.__dict__.items():
        # Ignore Optik specific arguments
        if (
            arg
            not in [
                "FILES",
                "max_iters",
                "debug",
                "cov_mode",
                "sender",
                "solver_timeout",
                "no_incremental",
                "incremental_threshold",
                "logs",
                "no_display",
            ]
            and not val is None
        ):
            cmdline += [f"--{arg.replace('_', '-')}", str(val)]
    cmdline += ["--format", "json"]
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

    display.stop_echidna_task_timer()
    return echidna_process
