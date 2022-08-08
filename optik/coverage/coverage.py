from typing import Dict, List, Optional
from dataclasses import dataclass
from maat import Constraint, MaatEngine, EVENT, WHEN
from ..common.exceptions import CoverageException
from ..common.world import WorldMonitor, EVMRuntime


@dataclass(eq=True, frozen=True)
class CoverageState:
    """Abstract base class that represents a "state" in the sense of
    coverage. If we track instructions, a state can be the covered
    instruction addresses, if we track paths, a state can be an
    execution path, ...

    Attributes:
        contract    Address of the contract being run
        contract_is_initialized     Whether we are running the init bytecode or the runtime bytecode
    """

    contract: int
    contract_is_initialized: bool


@dataclass(frozen=True)
class Bifurcation:
    """Dataclass recording a conditional branch point in code

    Attributes
        inst_addr       Address of the branching instruction
        taken_target    Address of instruction that was jumped to
        alt_target      Address of alternative instruction, that wasn't jumped to
        path_constraints    Path constraints that led to this bifurcation
        alt_target_constraint   Constraint to satisfy in order to invert the bifurcation
        input_uid       UID of the input that led to this bifurcation
        alt_state       Optional. Coverage state of the bifurcation alt target
    """

    inst_addr: int
    taken_target: int
    alt_target: int
    path_constraints: List[Constraint]
    alt_target_constraint: Constraint
    input_uid: str
    alt_state: Optional[CoverageState] = None

    def __eq__(self, other: object) -> bool:
        """Two bifurcations are equivalent if they branch to the same
        coverage state"""
        return (
            isinstance(other, Bifurcation) and self.alt_state == other.alt_state
        )

    def __hash__(self) -> int:
        """Custom hash based only on the target and transaction number"""
        return hash(self.alt_state)


class Coverage(WorldMonitor):
    """An abstract base class for computing coverage of a contract's code. It
    can be used to track standalone engines, or track a deployed contract
    when attached as WorldMonitor

    Attributes:
        covered         A dict mapping instruction addresses with the number of times
                        they have been executed
        bifurcations    A list of possible bifurcations
        current_input   The UID of the input currently being tracked
        contract        Optional contract to track. Used only when registered
                        as a WorldMonitor
    """

    # Class UID used to create unique names for Maat hooks
    # This variable needs to be redefined by child classes
    HOOK_ID = "__coverage"

    def __init__(self) -> None:
        super().__init__()
        self.covered: Dict[CoverageState, int] = {}
        self.bifurcations: List[Bifurcation] = []
        self.current_input: str = "<unspecified>"

    def get_state(self, **kwargs) -> CoverageState:
        """Abstract base method that returns the current coverage state"""
        raise CoverageException(
            "This method must be overloaded by child classes"
        )

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
        alt_state = self.get_state(inst_addr=alt_target, engine=m)
        if alt_state not in self.covered:
            self.bifurcations.append(
                Bifurcation(
                    inst_addr=m.info.addr,
                    taken_target=taken_target,
                    alt_target=alt_target,
                    path_constraints=list(
                        m.path.get_related_constraints(alt_constr)
                    ),
                    alt_target_constraint=alt_constr,
                    input_uid=self.current_input,
                    alt_state=alt_state,
                )
            )

    def track(self, m: MaatEngine) -> None:
        """Set hooks to track coverage on a symbolic engine"""
        m.hooks.add(
            EVENT.PATH,
            WHEN.BEFORE,
            callbacks=[self.branch_callback],
            name=f"{type(self).HOOK_ID}_branch_hook",
            data=self,
            group=f"{type(self).HOOK_ID}",
        )

    def set_input_uid(self, input_uid: str) -> None:
        """Set the input UID of the input currently running

        :param input_uid: the unique ID of the input that will be run by 'm'
        """
        self.current_input = input_uid

    def filter_bifurcations(self, visit_max: int = 0) -> None:
        """Filter the saved bifurcations to keep only the ones
        that will lead to new coverage states.

        :param visit_max: Keep the bifurcations if they lead to instructions
        that have been visited at most 'visit_max'
        """
        self.bifurcations = [
            b
            for b in self.bifurcations
            if self.covered.get(b.alt_state, 0) <= visit_max
        ]

    def sort_bifurcations(self) -> None:
        """Sort bifurcations according to their number of path constraints, from
        less constraints to more constraints"""
        self.bifurcations.sort(key=lambda x: len(x.path_constraints))

    @staticmethod
    def branch_callback(m: MaatEngine, cov: "Coverage") -> None:
        cov.record_branch(m)

    #### WorldMonitor interface
    def on_attach(self, address: int, **kwargs) -> None:
        """WorldMonitor interface callback to start tracking a contract"""
        for contract in self.world.contracts.values():
            for rt in contract.runtime_stack:
                self.track(rt.engine)

    def on_new_runtime(self, rt: EVMRuntime) -> None:
        """WorldMonitor interface callback to track new engines created by
        re-entrency"""
        self.track(rt.engine)
