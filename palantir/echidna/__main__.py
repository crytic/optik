from ..common.abi import call
from maat import *


def main() -> None:
    call_data = call(
        "foo",
        "(uint256, uint256, uint256, uint256)",
        0x1234567,
        45,
        Var(8, "a"),
        Var(300, "b"),
    )
    print(call_data)


if __name__ == "__main__":
    main()
