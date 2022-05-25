from maat import ARCH, MaatEngine, Info
from typing import List
from dataclasses import dataclass
import itertools


class EVMRuntime:
    """A wrapper class for executing a single transaction in a deployed contract"""

    def __init__(self, engine: MaatEngine, tx: EVMTransaction):
        self.engine = engine
        contract(self.engine).transaction = tx
        self.init_state = self.engine.take_snapshot()

    def run(self) -> Info:
        """Run the EVM, handling potential reverts"""
        self.engine.run()
        info = self.engine.info
        # TODO(boyan): check for potential errors (STOP.ERROR, STOP.FATAL)
        # and raise exception if any

        # If ended in revert, revert the state
        if info.stop == STOP.EXIT and info.exit_status == EVM.REVERT:
            self.engine.restore_snapshot(self.init_state)

        # Return info before potential revert
        return info


class ContractRunner:
    """A wrapper class that offers an interface to deploy a contract and handle execution of several transactions with potential re-entrency"""

    # TODO(boyan): support passing deployment address, etc
    def __init__(self, contract_file: str):
        self._transactions: Optional[List[EVMTransaction]] = None

        # Load the contract in a symbolic engine
        self.root_engine = MaatEngine(ARCH.EVM)
        self.root_engine.load(contract_file)

        # The wrapper holds a stack of pending runtimes. Each runtime represents
        # one transaction call inside the contract. The first runtime in the list
        # is the first transaction, the next ones are re-entrency calls into the
        # same contract
        self.runtime_stack: List[EVMRuntime] = []

    @property
    def current_runtime(self) -> EVMRuntime:
        return self.runtime_stack[-1]

    def push_runtime(self, tx: EVMTransaction) -> EVMRuntime:
        """Send a new transaction to the contract

        :param tx: The incoming transaction for which to create a new runtime
        :return: The new runtime created to execute 'tx'
        """
        # TODO(boyan): new_engine = self.root_engine.duplicate()
        # We should duplicate the engine. The code below works only
        # if there is no re-entrency and for a single transaction...
        if self.runtime_stack:
            raise GenericException("Re-entrency is not yet supported")
        self.runtime_stack.append(EVMRuntime(new_engine, tx))

    def pop_runtime(self) -> None:
        """Remove the top-level runtime"""
        self.runtime_stack.pop()


class EVMWorld:
    """Wrapper class for deploying and running multiple contracts potentially interacting with each other"""

    # TODO(boyan)
    # - snapshoting interface
    # - serialization interface
    # - calls accross contracts
    # - error handling when executing a contract
    # Note: this class should basically have the same API as MaatEngine so that
    # all exploration algorithms, etc, can work on the whole EVM world seamlessly
    pass
