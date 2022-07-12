from setuptools import setup, find_packages

version = "0.0.1"

# Lint
lint_deps = ["black~=22.0"]
# Tests
tests_deps = ["pytest"]

# Setup
setup(
    name="optik",
    description="TODO",
    url="https://github.com/trailofbits/optik",
    author="Trail of Bits",
    version=version,
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.7",
    install_requires=[
        "crytic-compile",
        "pymaat>=0.6.2",
        "eth_abi",
        "pysha3",
        "rlp"
    ],
    extras_require = {
        "lint": lint_deps,
        "tests": tests_deps,
    },
    entry_points={
        "console_scripts": [
            "hybrid-echidna = optik.echidna.__main__:main"
        ]
    },
)