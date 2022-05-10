from dataclasses import dataclass, field
from maat import Constraint
from typing import List


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
    """

    inst_addr: int
    taken_target: int
    alt_target: int
    path_constraints: List[Constraint]
    alt_target_constraint: Constraint
    input_uid: str
