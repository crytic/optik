from dataclasses import dataclass, field
from maat import Constraint
from typing import Any, List, Optional


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
        ctx_info        Optional. Contextual information about the bifurcation.
                        It can be the tx number, the execution path, etc.
    """

    inst_addr: int
    taken_target: int
    alt_target: int
    path_constraints: List[Constraint]
    alt_target_constraint: Constraint
    input_uid: str
    ctx_info: Optional[Any] = None

    def __eq__(self, other):
        """Two bifurcations are equivalent if they branch to the same
        alternative target, and if their transaction number is the same
        (or both are None)"""
        if self.alt_target != other.alt_target:
            return False
        else:
            return self.ctx_info == other.ctx_info

    def __hash__(self):
        """Custom hash based only on the target and transaction number"""
        hashable_ctx_info = (
            tuple(self.ctx_info)
            if isinstance(self.ctx_info, list)
            else self.ctx_info
        )
        return hash(
            (
                self.alt_target,
                hashable_ctx_info,
            )
        )
