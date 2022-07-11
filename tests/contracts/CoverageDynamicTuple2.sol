pragma solidity ^0.7.1;
pragma experimental ABIEncoderV2;

contract CoverageDynamicTuple2 {

    struct S { bytes10[5] x; uint16 y;}
    struct T { S x; uint128[4][] y; uint32 z;}

    function explore_me(T memory tup) public returns (uint256) {
        if (tup.z != 0 && ((tup.z>>2) == 0x12546)){
            return 0; // test::coverage
        } else if (tup.x.y*4 == 0x4848){
            return 1;
        } else if (tup.x.x.length >= 2 && tup.x.x[2] == tup.x.x[0] && tup.x.x[1] == "z"){
            return 2;
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