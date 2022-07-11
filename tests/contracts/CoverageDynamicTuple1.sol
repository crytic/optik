pragma solidity ^0.7.1;
pragma experimental ABIEncoderV2;

contract CoverageDynamicTuple1 {

    struct T { uint32 x; uint128[4][] y; uint32 z;}

    function explore_me(T memory tup) public returns (uint256) {
        if (tup.x != 0 && tup.z != 0 && ((tup.x>>103)&0xf == (tup.z>>88)&0xe)){
            return 0; // test::coverage
        } else {
            if (tup.y.length >= 1) {
                if (tup.y[0][2] >> 27 == tup.y[0][3])
                    return 1; // test::coverage
                else if (tup.y[0][0] >> 8 == 0x654651365165465146515145)
                    return 2; // test::coverage
                else
                    return 3; // test::coverage
            }
        }
    }
}