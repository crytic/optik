from maat import (
    ARCH,
    contract,
    EVMTransaction,
    increment_block_number,
    increment_block_timestamp,
    Info,
    MaatEngine,
    new_evm_runtime,
    STOP,
    TX_RES,
    Value,
    VarContext,
)
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass
import enum
from .exceptions import WorldException
from .util import compute_new_contract_addr


@dataclass(frozen=True)
class AbstractTx:
    """Abstract transaction. This class holds an EVMTransaction object with
    abstract transaction data, along with a VarContext that can contain
    concrete values for concolic variables present in the transacton data

    Attributes:
        tx      The full EVM transaction object
        ctx     The symbolic context associated with tx.data
    """

    tx: EVMTransaction
    block_num_inc: Value
    block_timestamp_inc: Value
    ctx: VarContext


class EVMRuntime:
    """A wrapper class for executing a single transaction in a deployed
    contract"""

    def __init__(self, engine: MaatEngine, tx: AbstractTx):
        self.engine = engine
        # Load the var context of the transaction in the engine
        self.engine.vars.update_from(tx.ctx)
        # Set transaction data in contract
        contract(self.engine).transaction = tx.tx
        self.init_state = self.engine.take_snapshot()

    def run(self) -> Info:
        """Run the EVM. If the code ends in a REVERT, the state is
        not automatically reverted. See EVMRuntime.revert()
        """
        self.engine.run()
        # Return info before potential revert
        return self.engine.info

    def revert(self) -> None:
        """Revert any state modifications performed while running"""
        self.engine.restore_snapshot(self.init_state, remove=False)


class ContractRunner:
    """A wrapper class that offers an interface to deploy a contract and
    handle execution of several transactions with potential re-entrency"""

    def __init__(
        self,
        root_engine: MaatEngine,
        contract_file: str,
        address: int,
        deployer: int,
    ):
        # Create a new engine that shares the variables context of the
        # root engine, but has its own memory (to hold its own runtime bytecode)
        self.root_engine = root_engine._duplicate(share={"vars"})
        # Load the contract the new symbolic engine
        self.root_engine.load(
            contract_file,
            envp={"address": f"{address:x}", "deployer": f"{deployer:x}"},
        )
        # The wrapper holds a stack of pending runtimes. Each runtime represents
        # one transaction call inside the contract. The first runtime in the list
        # is the first transaction, the next ones are re-entrency calls into the
        # same contract
        self.runtime_stack: List[EVMRuntime] = []
        # Contract nonce, starts at 1 as per EIP-161
        self.nonce = 1

    @property
    def current_runtime(self) -> EVMRuntime:
        return self.runtime_stack[-1]

    def push_runtime(self, tx: AbstractTx) -> EVMRuntime:
        """Send a new transaction to the contract

        :param tx: The incoming transaction for which to create a new runtime
        :return: The new runtime created to execute 'tx'
        """
        # Create a new engine that shares runtime code and symbolic
        # variables
        new_engine = self.root_engine._duplicate(share={"memory", "vars"})
        # Create new maat contract runtime for new engine
        new_evm_runtime(new_engine, self.root_engine)
        self.runtime_stack.append(EVMRuntime(new_engine, tx))

    def pop_runtime(self) -> None:
        """Remove the top-level runtime"""
        self.runtime_stack.pop()


class WorldMonitor:
    """Abstract interface for monitors that can execute callbacks on
    certain events"""

    def __init__(self):
        self.world: "EVMWorld" = None

    def on_attach(self, *args) -> None:
        """Callback called once when the monitor is attached to
        an EVMWorld"""
        pass

    def on_transaction(self, tx: EVMTransaction) -> None:
        """New transaction starts to be executed. This callback is triggered
        only for transactions and NOT for message calls between contracts"""
        pass

    def on_new_runtime(self, rt: EVMRuntime) -> None:
        """New EVM runtime created. This corresponds to a new transaction
        being run or execution of a message call accross contracts"""
        pass


class EVMWorld:
    """Wrapper class for deploying and running multiple contracts
    potentially interacting with each other

    Attributes:
        contracts       A dict mapping deployment addresses to a contract runner
        call_stack      A stack holding the addresses of the contracts in which
                        method calls are currently being executed. The same address
                        can appear twice in case of re-entrency
        tx_queue        A list of transactions to execute
        monitors        A list of WorldMonitor that can execute callbacks on
                        various events
    """

    def __init__(self):
        self.contracts: Dict[int, ContractRunner] = {}
        self.call_stack: List[int] = []
        self.tx_queue: List[AbstractTx] = []
        self.monitors: List[WorldMonitor] = []
        # Counter for transactions being run
        self._current_tx_num: int = 0
        # Root engine
        self.root_engine = MaatEngine(ARCH.EVM)

    def deploy(
        self, contract_file: str, address: int, deployer: int
    ) -> ContractRunner:
        """Deploy a contract at a given address

        :param contract_file: compiled contract file
        :param address: address where to deploy the contract
        :param deployer: address of the account deploying the contract
        """
        if address in self.contracts:
            raise WorldException(
                f"Couldn't deploy {contract_file}, address {address} already in use"
            )
        else:
            runner = ContractRunner(
                self.root_engine, contract_file, address, deployer
            )
            self.contracts[address] = runner
            return runner

    def push_transaction(self, tx: AbstractTx) -> None:
        """Add a new transaction in the transaction queue"""
        self.tx_queue.append(tx)

    def push_transactions(self, tx_list: List[AbstractTx]) -> None:
        """Add a list of transactions in the transaction queue. The transactions
        are executed in the order they have in the list"""
        for tx in tx_list:
            self.push_transaction(tx)

    def next_transaction(self) -> AbstractTx:
        """Return the next transaction to execute and remove it from the
        transaction queue"""
        res = self.tx_queue[0]
        self.tx_queue.pop(0)
        return res

    @property
    def current_tx_num(self) -> int:
        return self._current_tx_num

    @property
    def has_pending_transactions(self) -> bool:
        """True if the transaction queue is not empty"""
        return self.tx_queue

    @property
    def current_contract(self) -> ContractRunner:
        """Return the contract currently being executed"""
        if not self.call_stack:
            raise WorldException("No contract being currently executed")
        return self.contracts[self.call_stack[-1]]

    def get_contract(self, address: int) -> ContractRunner:
        """Return the contract deployed at 'address'"""
        if not address in self.contracts:
            raise WorldException(f"No contract deployed at {address}")
        return self.contracts[address]

    @property
    def current_engine(self) -> MaatEngine:
        """Return the MaatEngine in which code is currently being executed"""
        return self.current_contract.current_runtime.engine

    def run(self) -> STOP:
        """Run pending transactions"""

        if not (self.has_pending_transactions or self.call_stack):
            raise WorldException("No more transactions to execute")

        # Keep running as long as there are pending transactions
        # or unfinished nested message calls
        while self.has_pending_transactions or self.call_stack:
            if not self.call_stack:
                # Pop next transaction to execute
                tx = self.next_transaction()
                self._current_tx_num += 1
                # Find contract runner for the target contract
                contract_addr = tx.tx.recipient
                try:
                    runner = self.contracts[contract_addr]
                except KeyError as e:
                    raise WorldException(
                        f"Transaction recipient is {contract_addr}, but no contract is deployed there"
                    )
                # Create new runtime to run this transaction
                runner.push_runtime(tx)
                # Add to call stack
                self.call_stack.append(contract_addr)
                # Update block number & timestamp
                self._update_block_info(self.root_engine, tx)
                # Monitor events
                self._on_event(
                    "transaction",
                    contract(runner.current_runtime.engine).transaction,
                )
                self._on_event("new_runtime", runner.current_runtime)

            # Get current runtime and run
            rt: EVMRuntime = self.current_contract.current_runtime
            info = rt.run()
            stop = info.stop
            # Check stop reason
            if stop == STOP.EXIT:
                # Handle revert. WARNING: Once we revert the state, 'info' is
                # no more valid, because it is restored as well
                # Note: doing exit_status.as_uint() is safe here because
                # exit_status will never be symbolic for the EVM architecture
                if info.exit_status.as_uint() == TX_RES.REVERT:
                    rt.revert()
                # Call exited, delete the runtime
                self.current_contract.pop_runtime()
                # Remove it from callstack
                self.call_stack.pop()
                # TODO(boyan): handle tx return data if this runtime was
                # called by another contract
            elif stop == STOP.NONE and contract(rt.engine).outgoing_transaction:
                if out_tx.type in [TX.CREATE, TX.CREATE2]:
                    self._handle_CREATE()
                # TODO(boyan): other tx types, CALL, DELEGATECALL, ...
                else:
                    raise WorldException(
                        "Contract emitted an unsupported transaction type"
                    )

            # Any other return reason: event hook, error, ... -> we stop
            else:
                break

        return stop

    def _handle_CREATE(self) -> None:
        """Handle deployment of a new contract by another contract with
        the CREATE or CREATE2 EVM instructions. This method deploys the new
        contract, sets the address of the new contract in the caller's
        stack, and finally resets the 'outgoing_transaction' information
        from the caller runtime"""

        rt: EVMRuntime = self.current_contract.current_runtime
        out_tx = contract(rt.engine).outgoing_transaction
        deployer = out_tx.sender.as_uint(rt.engine.vars)

        # Get address of new contract
        if out_tx.type == TX.CREATE:
            new_contract_addr = compute_new_contract_addr(
                deployer, self.current_contract.nonce
            )
        else:
            # TODO(boyan): support CREATE2
            raise WorldException("Not implemented")
        # Increment caller nonce
        self.current_contract.nonce += 1
        # Deploy contract
        self.deploy_bytecode(out_tx.data, new_contract_addr, deployer)
        # Push new address as result in caller's stack
        contract(rt.engine).stack.push(Value(256, new_contract_addr))
        # Reset outgoing_transaction in caller
        contract(rt.engine).outgoing_transaction = None

    def _update_block_info(self, m: MaatEngine, tx: AbstractTx) -> None:
        """Increase the block number and block timestamp when emulating
        a new transaction

        :param m: any MaatEngine running in the Ethereum environment
        for which we want to update the block info
        :param tx: transaction data containing the block info increments
        """
        # Update block info in Maat
        increment_block_number(m, tx.block_num_inc)
        increment_block_timestamp(m, tx.block_timestamp_inc)
        # TODO(boyan): Should we add constraints to force time increments to
        # be within certain bounds?

    def attach_monitor(self, monitor: WorldMonitor, *args) -> None:
        """Attach a WorldMonitor"""
        if monitor in self.monitors:
            raise WorldException("Monitor already attached")
        self.monitors.append(monitor)
        monitor.world = self
        monitor.on_attach(*args)

    def detach_monitor(self, monitor: WorldMonitor) -> None:
        """Detach a WorldMonitor"""
        if monitor not in self.monitors:
            raise WorldException("Monitor was not attached")
        self.monitors.remove(monitor)

    def _on_event(self, event_name: str, *args) -> None:
        for m in self.monitors:
            callback = getattr(m, f"on_{event_name}")
            callback(*args)
