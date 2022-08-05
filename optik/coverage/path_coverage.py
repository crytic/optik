import itertools
from dataclasses import dataclass, field
from typing import Dict, List

from maat import MaatEngine

from .coverage import Coverage, CoverageState


@dataclass(frozen=True)
class PathCoverageState(CoverageState):
    path: List[int]

    def __eq__(self, other) -> bool:
        return (
            super(PathCoverageState, self).__eq__(other)
            and self.path == other.path
        )

    def __hash__(self):
        return hash(
            tuple(self.path)
            + (
                self.contract,
                self.contract_is_initialized,
            )
        )


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

    def get(self, path: List[int], default: int = 0) -> int:
        """Get number of times a given path was covered

        :param path: path for which to return coverage
        :param default: default value to return if 'path' not in the tree
        """
        if isinstance(path, PathCoverageState):
            path = path.path

        if path:
            addr = path[0]
            if addr in self.nodes:
                return self.nodes[addr].get(path[1:], default)
            return default
        return self.covered

    def __contains__(self, item: List[int]) -> bool:
        return self.get(item) > 0


class PathCoverage(Coverage):
    """A class for computing path coverage in a contract's code

    Attributes:

        bifurcations    A list of possible bifurcations
        current_input   The UID of the input currently being tracked
        contract        Optional contract to track. Used only when registered
                        as a WorldMonitor
    """

    def __init__(self) -> None:
        super().__init__()
        self.covered = PathTree()
        # Current path: list of symbolic branches that were taken
        self.current_path: List[int] = []

    def get_state(self, inst_addr: int, **kwargs) -> PathCoverageState:
        """Get coverage state for the path consisting in the current
        path + a branch to 'inst_addr'
        """
        return PathCoverageState(
            self.world.current_contract.address,
            self.world.current_contract.initialized,
            self.current_path + [inst_addr],
        )

    def record_branch(self, m: MaatEngine) -> None:
        super().record_branch(m)

        # Update current path and record it
        b = m.info.branch
        taken_target = (
            b.target.as_uint(m.vars) if b.taken else b.next.as_uint(m.vars)
        )
        self.current_path.append(taken_target)
        self.covered.add(self.current_path)

    def set_input_uid(self, input_uid: str) -> None:
        super().set_input_uid(input_uid)
        self.current_path = []


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


class RelaxedPathCoverage(PathCoverage):
    """Similar to PathCoverage, but if a path is covered, we consider that
    all subpaths"""

    HOOK_ID = "__relaxed_path_coverage"

    def __init__(self) -> None:
        super().__init__()

    def record_branch(self, m: MaatEngine) -> None:
        """Record execution of a symbolic branch and save the bifurcation
        point information"""

        super().record_branch(m)

        # In relaxed mode we also add sub paths to coverage tree
        # When running this, super() has already updated the current
        # path with the branch being taken
        for p in all_subpaths(self.current_path):
            self.covered.add(p)
