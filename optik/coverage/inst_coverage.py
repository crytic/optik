from .coverage import Coverage, CoverageState
from dataclasses import dataclass
from maat import MaatEngine, EVENT, WHEN


@dataclass(eq=True, frozen=True)
class InstCoverageState(CoverageState):
    inst_addr: int


class InstCoverage(Coverage):
    """Track instruction coverage on a smart contract's code"""

    HOOK_ID = "__inst_coverage"

    def __init__(self):
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
        return InstCoverageState(inst_addr)

    @staticmethod
    def inst_callback(m: MaatEngine, cov: "Coverage"):
        cov.record_exec(m)


@dataclass(eq=True, frozen=True)
class InstTxCoverageState(CoverageState):
    inst_addr: int
    tx_num: int


class InstTxCoverage(InstCoverage):
    """Track instruction coverage for a smart contract code, with
    transaction number sensitivity. This means that reaching instruction
    123 during transaction 0 is considered different than reaching
    instruction 123 during transaction 1, or 2, ..."""

    HOOK_ID = "__inst_tx_coverage"

    def __init__(self):
        super().__init__()

    def get_state(self, inst_addr: int, **kwargs) -> InstTxCoverageState:
        return InstTxCoverageState(inst_addr, self.world.current_tx_num)
