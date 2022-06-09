pragma solidity ^0.7.1;

contract BoolArg {

    function testBool(bool x, uint128 y) public returns (int16) {
        if (y > 0x8000000 || x) {
            if (y % 0x10000 == 0) {
                return 3; // test::coverage
            }

            return 5; // test::coverage
        }

        return 10; // test::coverage
    }
}