pragma solidity ^0.7.1;

contract CoverageInt {
    function explore_me(int128 x) public returns (int16)
    {
        if (x-265 > 3) {
            return 5; // test::coverage
        } else if (x*2 == -42) {
            return 7; // test::coverage
        } else {
            if ((x-11) % 2 == 0) {
                return 1; // test::coverage
            } else if (x/4 == -50){
                return 0; // test::coverage
            }
        }
    }
}