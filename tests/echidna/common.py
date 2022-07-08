import tempfile
from pathlib import Path
from typing import Optional

CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "contracts"

def new_test_dir(parent: Optional[str] = None) -> str:
    """Create and return path to a temporary test directory
    located inside the 'parent' directory, or a default directory
    if 'parent' is None"""
    return tempfile.TemporaryDirectory(dir=parent).name
