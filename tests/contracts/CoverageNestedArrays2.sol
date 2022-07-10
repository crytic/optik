pragma solidity ^0.7.1;
pragma experimental ABIEncoderV2;

contract CoverageNestedArrays2 {

    function explore_me(uint32[4][] memory x) pure public returns (int8) {

        if (x.length >= 3){
            if (x[1][3] == 8 && x[1][2] == 15)
                return 1; // test::coverage
            else if (x[1][0] == 111111)
                return 4; // test::coverage
        }

        if ( (x.length > 1) && ((x[0][3] >> 3) & 0xFF) == 0x73) {
            return 2; // test::coverage
        } else {
            return 7; // test::coverage
        }
    }
}
