pragma solidity ^0.7.1;
pragma experimental ABIEncoderV2;

contract CoverageNestedTuple {
    uint256 a = 0;

    struct T { uint x; uint y; }
    struct S { uint a; T b; }
    
    function explore_me(S memory tup) public returns (uint256) {

        if (tup.a > 0x800000){
            if (((tup.b.x >> 18) & 0xff == 0x41) && (tup.b.x > 0x800000000) && (tup.b.y >>18)&0xff == 0xd9){
                a = 9; // test::coverage
            }else{
                a = 10; // test::coverage
            }  
        }
        return a; // test::coverage
    }
}
