from ..common.abi import call
from maat import *


def main() -> None:
    call_data = call("foo", "(uint256, uint256)", 12345678, 45)
    print(call_data)


if __name__ == "__main__":
    main()