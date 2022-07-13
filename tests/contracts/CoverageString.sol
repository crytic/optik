pragma solidity ^0.7.1;

contract CoverageString {
    bytes16 key = "\xf8JU\xa998J248DJNS\x014";
    bool state = false;

    function f(string memory s1) public returns (int) {

        bytes memory x = bytes(s1);

        if (x.length >= 4 && x.length <= 10) {
            if (x[0] == x[3]) {
                return 3; // test::coverage
            }

            if (uint8(x[1]) >> 2 == uint8(x[2]) >> 1) {
                return 1; // test::coverage
            }

            if (uint16(uint8(x[1])) + 2*uint16(uint8(x[2])) + 3*uint16(uint8(x[3])) == 0x167) {
                return 101; // test::coverage
            } 

            for (uint8 i = 0; i < 3; i++) {
                if (x[i+1]  == key[i]) { 
                    state = true;
                }
            }

            if (state) {
                return 2; // test::coverage
            } else {
                return 4; // test::coverage
            }

        } else {
            return 5; // test::coverage
        }

    }
}