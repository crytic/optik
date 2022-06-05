import random
import string
import os
from pathlib import Path
from typing import Final, List

CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "contracts"


def new_test_dir(parent: str) -> str:
    """Create and return path to a temporary test directory
    located inside the 'parent' directory"""
    random_dir = "".join(
        random.choice(string.ascii_lowercase) for _ in range(10)
    )
    return os.path.join(parent, random_dir)
