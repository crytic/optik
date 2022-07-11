pragma solidity ^0.7.1;
pragma experimental ABIEncoderV2;

contract CoverageDynamicTuple3 {

    struct S { bytes10[] x; bytes14 y;}
    struct T { uint32 x; uint128[4][1] y; S[3][1] z;}

    function explore_me(T memory tup) public returns (uint256) {
        if (tup.x > 0x12345){
            return 0; // test::coverage
        } else if (tup.y.length > 0) {
            if (tup.y[0][3] >> 20 == 0x1111111111)
                return 1; // test::coverage
        }

        if (tup.z.length > 0 && tup.z[0][2].x.length > 0) {
            if (tup.z[0][2].x[0][9] == tup.z[0][2].y[11])
                if (uint8(tup.z[0][2].x[0][8])>>2 == 0x11)
                    return 7; // test::coverage
                else
                    return 2; // test::coverage
            else if (tup.z[0][2].x[0][3] == tup.z[0][2].y[10])
                return 3; // test::coverage
            else
                return 4; // test::coverage
        }

        return 5;
    }
}