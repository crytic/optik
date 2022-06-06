from dataclasses import dataclass, field
from maat import Constraint
from typing import List, Optional


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
        tx_num          Optional. Position in the input's transaction list of
                        the transaction being executed when the bifurcation
                        is recorded
    """

    inst_addr: int
    taken_target: int
    alt_target: int
    path_constraints: List[Constraint]
    alt_target_constraint: Constraint
    input_uid: str
    tx_num: Optional[int] = None

    def __eq__(self, other):
        """Two bifurcations are equivalent if they branch to the same
        alternative target, and if their transaction number is the same
        (or both are None)"""
        if self.alt_target != other.alt_target:
            return False
        else:
            return self.tx_num == other.tx_num

    def __hash__(self):
        """Custom hash based only on the target and transaction number"""
        return hash(
            (
                self.alt_target,
                self.tx_num,
            )
        )
