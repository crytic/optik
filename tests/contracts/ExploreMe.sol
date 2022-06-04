pragma solidity ^0.7.1;

contract ExploreMe {
    uint256 a = 0;
    
    function explore_me(uint256 x) public returns (uint256) {
        if (x > 0x80000000000000000){
            if (x % 0x10000 == 0){
                if ((x>>104)&1 == (x>>96)&1){
                    if (x / 0x10000 == 1634661910256948115582236828960324758669073336040947712){
                        a = 1;   // test::coverage
                    }else{
                        a = 2;   // test::coverage
                    }
                }else{
                    if (x/0x10000 % 2 == 0){
                        a = 3;   // test::coverage
                    }else{
                        a = 4;    // test::coverage       
                   }
               }
            }else{
               if ((x>>103)&0xf == (x>>88)&0xe && (x>>104)&0xf == 0xd){
                   a = 5;
               }else{
                   a = 6;   // test::coverage
               }
            }
        }else{
           if (x % 123456 == 0){
               if( x / 123456 == 478){
                   a = 7;    // test::coverage
               // TODO(boyan): test with bitwise OR
               }else if(((x/123456) ^ 22) == 0xabba){
                   a = 8;   // test::coverage
               }
           }else{
               if (x & 0xff == ((x >> 16)&0xff) 
                   && (x>>18)&0xff == 0xd9
               ){
                   a = 9;   // test::coverage
               }else{
                   a = 10;    // test::coverage
               }
           }
        }
        return a;
    }
}
