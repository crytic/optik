pragma solidity ^0.7.1;
pragma experimental ABIEncoderV2;

contract CoverageArrayOfTuple {

    struct S { bytes10[2] x; bytes14 y;}

    function explore_me(S[] memory x) public returns (uint256) {
        if (x.length > 1)
            if (x[0].x.length > 1)
                if (x[0].x[1][2] == "z" && x[0].x[1][4] == "a")
                    return 0; // test::coverage
                else
                    return 1; // test::coverage
            else
                return 2;
        else
            return 3; // test::coverage
    }
}