pragma solidity ^0.7.1;
pragma experimental ABIEncoderV2;

contract CoverageNestedArrays1 {

    function explore_me(uint32[][2] memory x) pure public returns (int8) {

        if (x[1].length >= 3){
            if (x[1][0] == 3 && x[1][1] == 15)
                return 1; // test::coverage
            else
                return 4; // test::coverage
        }

        if ( (x[0].length > 1) && ((x[0][1] >> 3) & 0xFF) == 0x73) {
            return 2; // test::coverage
        } else {
            return 7; // test::coverage
        }
    }
}
