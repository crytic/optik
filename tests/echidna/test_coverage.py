from .common import new_test_dir, CONTRACTS_DIR
import pytest
import os
from typing import Optional
from optik.echidna import run_hybrid_echidna

COVERAGE_TARGET_MARKER = "test::coverage"

# List of contracts to test and coverage mode to use
to_test = [
    ("ExploreMe.sol", "inst"),
    ("Primality.sol", "inst"),
    ("MultiMagic.sol", "path-relaxed"),
]
to_test = [
    (
        CONTRACTS_DIR / contract_file,
        mode,
    )
    for contract_file, mode in to_test
]

# Test coverage on every contract
@pytest.mark.parametrize("contract,cov_mode", to_test)
def test_coverage(contract: str, cov_mode: str):
    """Test coverage for a given contract. The function
    runs hybrid echidna on the contract and asserts that all target lines in the
    source code were reached. It does so by looking at the `covered.<timestamp>.txt`
    file generated by Echidna after fuzzing, and making that every line marked
    with the coverage test marker was reached (indicated by '*').
    """
    test_dir = new_test_dir("/tmp/")
    # Run hybrid echidna
    cmdline_args = f"{contract}  --test-mode assertion --corpus-dir {test_dir} --seq-len 10 --seed 123456 --max-iters 10 --test-limit 10000 --cov-mode {cov_mode} --debug".split()
    run_hybrid_echidna(cmdline_args)
    # Check coverage
    covered_file = get_coverage_file(test_dir)
    assert (
        not covered_file is None
    ), f"Couldn't find coverage file in test dir {test_dir}"
    with open(covered_file, "r") as f:
        for i, line in enumerate(f.readlines()):
            if COVERAGE_TARGET_MARKER in line and not line[0] == "*":
                assert (
                    False
                ), f"Failed to cover line {i+1}:\n|{''.join(line.split('|')[1:])}"


def get_coverage_file(
    test_dir: str,
) -> Optional[str]:
    """Returns the path to covered.<timestamp>.txt file generated by echidna
    in the 'test_dir' directory. Returns None if no such file exists"""
    # Get the first file after reverse sorting the filename list, so
    # that we get the latest coverage file (name with the bigger timestamp)
    for filename in sorted(os.listdir(test_dir), reverse=True):
        if filename.startswith("covered.") and filename.endswith(".txt"):
            return os.path.join(test_dir, filename)
    return None
