pragma solidity ^0.7.1;

contract C {
    address owner;
    uint private stateA = 0;
    uint private stateB = 0;
    uint CONST = 32;

    constructor () {
        owner = msg.sender;
    }

    function f (uint x) public {
        if (msg.sender == owner) { 
            stateA = x;
        }
    }

    function g (uint y) public {
        if (stateA % CONST == 1) {
            stateB = y - 10;
        }
    }

    function h () public returns (uint) {
        if (stateB == 62)
            return 1; // test::coverage
        else
            return 2; // test::coverage
    }
}