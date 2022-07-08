pragma solidity ^0.7.1;

contract CoverageDynamicArray {
    
    function explore_me(uint32[] memory x) pure public returns (int8) {

        if (x.length >=8) {
            if (x[0] == 3 && x[7] == 15) {
                return 1; // test::coverage
            }

            if (((x[1] >> 3) & 0xFF) == 0x73) {
                return 2; // test::coverage
            } else {
                return 7; // test::coverage
            }
        } else {
            return 3; // test::coverage
        }
    }
}
