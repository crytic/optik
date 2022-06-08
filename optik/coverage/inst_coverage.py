from maat import MaatEngine, EVENT, WHEN
from typing import Dict, List, Optional
from ..common.exceptions import CoverageException
from ..common.world import WorldMonitor, EVMRuntime
from .bifurcation import Bifurcation
from dataclasses import dataclass


@dataclass(eq=True, frozen=True)
class CoverageState:
    inst_addr: int
    tx_num: Optional[int] = None


class InstCoverage(WorldMonitor):
    """A class for computing instruction coverage in a contract's code. It
    can be used to track standalone engines, or track a deployed contract
    when attached as WorldMonitor

    Attributes:
        covered         A dict mapping instruction addresses with the number of times
                        they have been executed
        bifurcations    A list of possible bifurcations
        current_input   The UID of the input currently being tracked
        contract        Optional contract to track. Used only when registered
                        as a WorldMonitor
        record_tx_num   If set to True, record tx number along with covered addresses
                        which results in more fine-grain coverage and more bifurcations
                        recorded. Default: False
    """

    def __init__(self, record_tx_num: bool = False):
        super().__init__()
        self.covered: Dict[CoverateState, int] = {}
        self.bifurcations: List[Bifurcation] = []
        self.current_input: str = "<unspecified>"
        self.contract: Optional[ContractRunner] = None
        # Options
        self.record_tx_num = record_tx_num

    @property
    def current_tx_num(self) -> Optional[int]:
        return self.world.current_tx_num if self.record_tx_num else None

    def record_exec(self, addr: int) -> None:
        """Record execution of instruction at 'addr'"""
        state = CoverageState(addr, self.current_tx_num)
        self.covered[state] = self.covered.get(state, 0) + 1

    def record_branch(self, m: MaatEngine) -> None:
        """Record execution of a symbolic branch and save the bifurcation
        point information"""
        b = m.info.branch
        if b.taken is None:
            raise CoverageException(
                "'taken' information missing from branch info"
            )
        # Record bifurcation point
        if b.taken is True:
            alt_target = b.next.as_uint(m.vars)
            taken_target = b.target.as_uint(m.vars)
            alt_constr = b.cond.invert()
        else:
            alt_target = b.target.as_uint(m.vars)
            taken_target = b.next.as_uint(m.vars)
            alt_constr = b.cond

        # Record only if bifurcation to code that was not yet covered
        target_state = CoverageState(alt_target, self.current_tx_num)
        if target_state not in self.covered:
            self.bifurcations.append(
                Bifurcation(
                    inst_addr=m.info.addr,
                    taken_target=taken_target,
                    alt_target=alt_target,
                    path_constraints=list(m.path.constraints()),
                    alt_target_constraint=alt_constr,
                    input_uid=self.current_input,
                    ctx_info=self.current_tx_num,
                )
            )

    def track(self, m: MaatEngine) -> None:
        """Set hooks to track instruction coverage for an Engine"""
        m.hooks.add(
            EVENT.EXEC,
            WHEN.BEFORE,
            callbacks=[InstCoverage.inst_callback],
            name="__inst_coverage_exec_hook",
            data=self,
            group="__inst_coverage",
        )
        m.hooks.add(
            EVENT.PATH,
            WHEN.BEFORE,
            callbacks=[InstCoverage.branch_callback],
            name="__inst_coverage_branch_hook",
            data=self,
            group="__inst_coverage",
        )

    def set_input_uid(self, input_uid: str) -> None:
        """Set the input UID of the input currently running

        :param input_uid: the unique ID of the input that will be run by 'm'
        """
        self.current_input = input_uid

    def filter_bifurcations(self, visit_max: int = 0) -> None:
        """Filter the saved bifurcations to keep only the ones
        that will lead to new code

        :param visit_max: Keep the bifurcations if they lead to instructions
        that have been visited at most 'visit_max'
        """
        self.bifurcations = [
            b
            for b in self.bifurcations
            if self.covered.get(CoverageState(b.alt_target, b.ctx_info), 0)
            <= visit_max
        ]

    def sort_bifurcations(self) -> None:
        """Sort bifurcations according to their number of path constraints, from
        less constraints to more constraints"""
        self.bifurcations.sort(key=lambda x: len(x.path_constraints))

    @staticmethod
    def inst_callback(m: MaatEngine, cov: "InstCoverage"):
        cov.record_exec(m.info.addr)

    @staticmethod
    def branch_callback(m: MaatEngine, cov: "InstCoverage"):
        cov.record_branch(m)

    #### WorldMonitor interface
    def on_attach(self, address: int) -> None:
        """WorldMonitor interface callback to start tracking a contract"""
        self.contract = self.world.get_contract(address)
        for rt in self.contract.runtime_stack:
            self.track(rt.engine)

    def on_new_runtime(self, rt: EVMRuntime) -> None:
        """WorldMonitor interface callback to track new engines created by
        re-entrency"""
        # If new runtime for the contract we track, track the associated MaatEngine
        if self.world.current_contract is self.contract:
            self.track(rt.engine)
