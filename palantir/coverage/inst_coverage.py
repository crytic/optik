from maat import MaatEngine, EVENT, WHEN
from typing import Dict, List
from ..common.exceptions import CoverageException
from .bifurcation import Bifurcation


class InstCoverage:
    """A class for computing instruction coverage in a contract's code

    Attributes:
        covered         A dict mapping instruction addresses with the number of times
                        they have been executed
        bifurcations    A list of possible bifurcations
        current_inputs  A dict mapping a MaatEngine UID to the UID of the input currently being
                        executed
    """

    def __init__(self):
        self.covered: Dict[int, int] = {}
        self.bifurcations: List[Bifurcation] = []
        self.current_inputs: Dict[int, str] = {}

    def record_exec(self, addr: int) -> None:
        """Record execution of instruction at 'addr'"""
        self.covered[addr] = self.covered.get(addr, 0) + 1

    def record_branch(self, m: MaatEngine) -> None:
        """Record execution of a symbolic branch and save the bifurcation
        point information"""
        input_uid: str = self.current_inputs.get(m.uid, "<unspecified>")
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
        if alt_target not in self.covered:
            self.bifurcations.append(
                Bifurcation(
                    inst_addr=m.info.addr,
                    taken_target=taken_target,
                    alt_target=alt_target,
                    path_constraints=list(m.path.constraints()),
                    alt_target_constraint=alt_constr,
                    input_uid=input_uid,
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

    def set_input_uid(self, m: MaatEngine, input_uid: str) -> None:
        """Set the input UID of the input currently running in an engine

        :param m: the engine that will run the input identified by 'input_uid'
        :param input_uid: the unique ID of the input that will be run by 'm'
        """
        self.current_inputs[m.uid] = input_uid

    def filter_bifurcations(self, visit_max: int = 0) -> None:
        """Filter the saved bifurcations to keep only the ones
        that will lead to new code

        :param visit_max: Keep the bifurcations if they lead to instructions
        that have been visited at most 'visit_max'
        """
        self.bifurcations = [
            b
            for b in self.bifurcations
            if self.covered.get(b.alt_target, 0) <= visit_max
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
