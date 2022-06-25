pragma solidity ^0.7.1;

contract CoverageBool {

    function f(bool x, uint128 y, bool z) public returns (int16) {
        if (y > 0x8000000 || x == z) {
            if ((y % 0x10000 == 0) == z) {
                return 3; // test::coverage
            }

            return 5; // test::coverage
        }
        if ((z || x) && y*3 == 33333){
            if (x) {
                return 1; // test::coverage
            } else {
                return 2; // test::coverage
            }
        }
 
        return 10; // test::coverage
    }
}