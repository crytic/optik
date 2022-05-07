from .abi import call
from maat import *


def main() -> None:
    call_data = call("foo", "(uint256, lalali)", 12345678)
    print(call_data)
