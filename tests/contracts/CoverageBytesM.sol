pragma solidity ^0.7.1;

contract CoverageBytesM {
    bytes16 key = "\xf8JU\xa998J248DJNS\x014";
    bool state = false;

    function f(bytes16 x) public returns (int) {
        state = true;
        for (uint8 i = 0; i < 16; i+=3) {
            if (uint8(x[i]) != uint8(key[i]) + 3){
                state = false;
                break;
            }
        }
        if (state)
            return 1; // test::coverage
        else
            return 0; // test::coverage
    }
}