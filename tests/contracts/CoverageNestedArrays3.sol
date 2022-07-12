pragma solidity ^0.7.1;
pragma experimental ABIEncoderV2;

contract CoverageNestedArrays3 {
    
    function explore_me(uint8[2][][4][] memory x) pure public returns (int8) {

        if (x.length > 4) {
            if (x[1][3].length > 3){
                if (x[1][3][0][0] >> 1 == 0x44)
                    return 1; // test::coverage
                else if (x[1][3][0][1] >> 2 == 0x22)
                    return 4; // test::coverage
            }

            if (x[1][2].length > 0){
                if (((x[1][2][0][1] + x[1][2][0][0]) & 0xFF) == 0x73)
                    return 2; // test::coverage
                else
                    return 7; // test::coverage
            }
        } else {
            return 3; // test::coverage
        }
    }
}
