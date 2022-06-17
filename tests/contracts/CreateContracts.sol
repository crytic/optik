pragma solidity ^0.7.1;

// Contract to test
contract CreateContracts {
    bool state = true;
    bool state2 = true;
    A a;
    A b;

    constructor() public {
        a = new A();
    }

    function f() public {
        if (b == A(address(0x0)))
            b = new A();
    }

    function g(address x) public {
        if (A(x) == a)
            state = false;
        if ((A(x) == b) && (b != A(address(0x0))))
            state2 = false;
    }

    function h() public returns (bool) {
        if (!(state || state2))
            return false; // test::coverage
        else
            return true; // test::coverage
    }
}

// TODO: test calling some function in A 
// TODO: test with a constructor that takes arguments

// Some dummy contract
contract A {
    uint a = 42;
    uint b = 43;

    function f() public {
        a = a+1;
    }
}