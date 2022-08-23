from dataclasses import dataclass
from typing import FrozenSet, Optional, List, Tuple
from maat import contract, MaatEngine, EVENT, WHEN
from ..common.world import AbstractTx
from .coverage import Coverage, CoverageState


@dataclass(eq=True, frozen=True)
class InstCoverageState(CoverageState):
    inst_addr: int


class InstCoverage(Coverage):
    """Track instruction coverage on a smart contract's code"""

    HOOK_ID = "__inst_coverage"

    def __init__(self) -> None:
        super().__init__()

    def track(self, m: MaatEngine) -> None:
        super().track(m)
        m.hooks.add(
            EVENT.EXEC,
            WHEN.BEFORE,
            callbacks=[self.inst_callback],
            name=f"{type(self).HOOK_ID}_exec_hook",
            data=self,
            group=f"{type(self).HOOK_ID}",
        )

    def record_exec(self, m: MaatEngine) -> None:
        """Record execution of instruction at 'addr'"""
        state = self.get_state(inst_addr=m.info.addr, engine=m)
        self.covered[state] = self.covered.get(state, 0) + 1

    def get_state(self, inst_addr: int, **kwargs) -> InstCoverageState:
        assert self.world
        # TODO (montyly) the class takes 1 parameter, but 3 are provided here?
        return InstCoverageState(
            self.world.current_contract.address,
            self.world.current_contract.initialized,
            inst_addr,
        )

    @staticmethod
    def inst_callback(m: MaatEngine, cov: "Coverage") -> None:
        cov.record_exec(m)


@dataclass(eq=True, frozen=True)
class InstTxCoverageState(InstCoverageState):
    tx_num: int


class InstTxCoverage(InstCoverage):
    """Track instruction coverage for a smart contract code, with
    transaction number sensitivity. This means that reaching instruction
    123 during transaction 0 is considered different than reaching
    instruction 123 during transaction 1, or 2, ..."""

    HOOK_ID = "__inst_tx_coverage"

    def __init__(self) -> None:
        super().__init__()

    def get_state(self, inst_addr: int, **kwargs) -> InstTxCoverageState:
        return InstTxCoverageState(
            self.world.current_contract.address,
            self.world.current_contract.initialized,
            inst_addr,
            self.world.current_tx_num,
        )


@dataclass(eq=True, frozen=True)
class InstSgCoverageState(InstCoverageState):
    storage_use: FrozenSet[int]


class InstSgCoverage(InstCoverage):
    """This class implements a notion of coverage that is storage-
    sensitive. It basically performs instruction coverage, but
    also includes the state of the contract's storage in the coverage
    information.

    The state of a contract's storage is the set of all storage addresses
    that hold a purely symbolic or non-null value
    """

    HOOK_ID = "__inst_sg_coverage"

    def __init__(self) -> None:
        super().__init__()

    def get_state(
        self, inst_addr: int, engine: MaatEngine, **kwargs
    ) -> InstSgCoverageState:
        return InstSgCoverageState(
            self.world.current_contract.address,
            self.world.current_contract.initialized,
            inst_addr,
            frozenset(
                [
                    addr
                    for addr, val in contract(engine).storage.used_slots()
                    if val.is_symbolic(engine.vars)
                    or val.as_uint(engine.vars) != 0
                ]
            ),
        )


@dataclass(eq=True, frozen=True)
class InstIncCoverageState(InstCoverageState):
    tx_num: int
    total_tx_cnt: int


class InstIncCoverage(InstCoverage):
    """Track instruction coverage for a smart contract code, with
    transaction number AND total number of transactions sensitivity.
    This means that reaching instruction
    123 during transaction 0 is considered different than reaching
    instruction 123 during transaction 1, or 2, ... and that reaching
    instruction 123 in a sequence of 3 transactions is different than reaching
    instruction 123 in a sequence of 4 transactions.
    This mode is used for the incremental mode of hybrid-echidna + feed-echidna
    """

    HOOK_ID = "__inst_inc_coverage"

    def __init__(self) -> None:
        super().__init__()
        self.total_tx_cnt = None

    def get_state(self, inst_addr: int, **kwargs) -> InstIncCoverageState:
        return InstIncCoverageState(
            self.world.current_contract.address,
            self.world.current_contract.initialized,
            inst_addr,
            self.world.current_tx_num,
            self.total_tx_cnt,
        )

    # WorldMonitor interface
    def on_attach(
        self, address: int, tx_seq: List[AbstractTx], **kwargs
    ) -> None:
        super().on_attach(address)
        self.total_tx_cnt = len(tx_seq)


@dataclass(eq=True, frozen=True)
class InstTxSeqCoverageState(InstCoverageState):
    tx_num: int
    tx_seq: Optional[Tuple]


class InstTxSeqCoverage(InstCoverage):
    """Track instruction coverage for a smart contract code, with
    transaction number AND tx sequence.
    This mode is used for the incremental mode of hybrid-echidna + feed-echidna
    """

    HOOK_ID = "__inst_tx_seq_coverage"

    def __init__(self, threshold: int):
        """
        :param threshold: the sequence length after which tx sequence information
        is ignored:
        """
        super().__init__()
        self.tx_seq: Optional[Tuple] = None
        self.threshold = threshold

    def get_state(self, inst_addr: int, **kwargs) -> InstTxSeqCoverageState:
        return InstTxSeqCoverageState(
            self.world.current_contract.address,
            self.world.current_contract.initialized,
            inst_addr,
            self.world.current_tx_num,
            self.tx_seq,
        )

    # WorldMonitor interface
    def on_attach(
        self, address: int, tx_seq: List[AbstractTx], **kwargs
    ) -> None:
        super().on_attach(address)
        # Extract the function selectors to build a "minimal" tx_seq
        self.tx_seq = tuple(
            [tx.tx.data[0].as_uint() for tx in tx_seq if tx.tx and tx.tx.data]
        )
