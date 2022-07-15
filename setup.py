from setuptools import setup, find_packages

# Setup
setup(
    packages=find_packages(exclude=["tests", "tests.*"]),

    entry_points={
        "console_scripts": [
            "hybrid-echidna = optik.echidna.__main__:main"
        ]
    },
)