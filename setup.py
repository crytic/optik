from setuptools import setup, find_packages

version = "0.0.1"

# Lint
lint_deps = ["black~=22.0"]

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
        "pymaat",
        "eth_abi"
    ],
    extras_require = {
        "lint": lint_deps,
    },
    entry_points={
        "console_scripts": [
            "hybrid-echidna = optik.echidna.__main__:main"
        ]
    },
)