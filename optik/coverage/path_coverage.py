from maat import MaatEngine, EVENT, WHEN
from typing import Dict, List, Optional
from ..common.exceptions import CoverageException
from ..common.world import WorldMonitor, EVMRuntime
from .bifurcation import Bifurcation
from dataclasses import dataclass, field
import itertools


@dataclass(frozen=False)
class PathTree:
    """Simple class that holds a tree of execution paths"""

    nodes: Dict[int, "PathThree"] = field(default_factory=lambda: {})
    covered: int = 0

    def add(self, path: List[int]) -> None:
        """Add a new path"""
        self.covered += 1
        if path:
            addr = path[0]
            if addr not in self.nodes:
                self.nodes[addr] = PathTree()
            self.nodes[addr].add(path[1:])

    def get(self, path: List[int]) -> int:
        """Get number of times a given path was covered"""
        if path:
            addr = path[0]
            if addr in self.nodes:
                return self.nodes[addr].get(path[1:])
            else:
                return 0
        return self.covered

    def __contains__(self, item: List[int]) -> bool:
        return self.get(item) > 0


def all_subpaths(path: List[int]) -> List[List[int]]:
    """Return all subpaths (ordered combinations) of 'path'.
    For example if path = [3,2,1] it shall return
    [[1], [2], [3], [3,2], [2,1], [3,1], [3,2,1]]
    """
    res = []
    for L in range(1, len(path) + 1):
        for subpath in itertools.combinations(path, L):
            res.append(list(subpath))
    return res


class PathCoverage(WorldMonitor):
    """A class for computing path coverage in a contract's code. It
    can be used to track standalone engines, or track a deployed contract
    when attached as WorldMonitor

    Attributes:

        bifurcations    A list of possible bifurcations
        current_input   The UID of the input currently being tracked
        contract        Optional contract to track. Used only when registered
                        as a WorldMonitor
    """

    def __init__(self, strict: bool = True):
        super().__init__()
        self.strict = strict
        self.covered = PathTree()
        self.bifurcations: List[Bifurcation] = []
        self.current_input: Optional[str] = None
        self.contract: Optional[ContractRunner] = None
        # Current path: list of symbolic branches that were taken
        self.current_path: List[int] = []

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
        alt_path = self.current_path + [alt_target]
        if alt_path not in self.covered:
            self.bifurcations.append(
                Bifurcation(
                    inst_addr=m.info.addr,
                    taken_target=taken_target,
                    alt_target=alt_target,
                    path_constraints=list(m.path.constraints()),
                    alt_target_constraint=alt_constr,
                    input_uid=self.current_input,
                    ctx_info=alt_path,
                )
            )

        # Update current path and record it
        self.current_path.append(taken_target)
        # If not in strict mode, also add the subpaths in coverage
        if self.strict:
            all_paths = [self.current_path]
        else:
            all_paths = all_subpaths(self.current_path)
        for p in all_paths:
            self.covered.add(p)

    def track(self, m: MaatEngine) -> None:
        """Set hooks to track path coverage for an Engine"""
        m.hooks.add(
            EVENT.PATH,
            WHEN.BEFORE,
            callbacks=[PathCoverage.branch_callback],
            name="__path_coverage_branch_hook",
            data=self,
            group="__path_coverage",
        )

    def set_input_uid(self, input_uid: str) -> None:
        """Set the input UID of the input currently running, and reset the
        current path information

        :param input_uid: the unique ID of the input that will be run by 'm'
        """
        self.current_input = input_uid
        self.current_path = []

    def filter_bifurcations(self, visit_max: int = 0) -> None:
        """Filter the saved bifurcations to keep only the ones
        that will lead to new code

        :param visit_max: Keep the bifurcations if they lead to instructions
        that have been visited at most 'visit_max'
        """
        self.bifurcations = [
            b
            for b in self.bifurcations
            if self.covered.get(b.ctx_info) <= visit_max
        ]

    def sort_bifurcations(self) -> None:
        """Sort bifurcations according to their number of path constraints, from
        less constraints to more constraints"""
        self.bifurcations.sort(key=lambda x: len(x.path_constraints))

    @staticmethod
    def branch_callback(m: MaatEngine, cov: "PathCoverage"):
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
