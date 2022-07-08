pragma solidity ^0.7.1;
pragma experimental ABIEncoderV2;

contract CoverageStaticTuple {
    uint256 a = 0;

    struct T { uint x; uint128 y; }
    
    function explore_me(T memory tup) public returns (uint256) {
                
        if ((tup.x>>103)&0xf == (tup.y>>88)&0xe) {
            a = 5; // test::coverage
        }else{
            a = 6; // test::coverage
            if (tup.x % 0x1000 == 0) {
                return 1;
            }
        }
        
        return a; // test::coverage
    }
}

