pragma solidity ^0.7.1;

// Contract to test
contract CreateContracts2 {
    bool state = true;
    bool state2 = true;
    A a;
    A b;

    function f() public {
        if (a == A(address(0x0)))
            a = new A();
        if (b == A(address(0x0)))
            b = new A();
    }

    function g1(address x) public {
        if (A(x) == a && (a != A(address(0x0))))
            state = false;
    }

    function g2(address x) public {
        if ((A(x) == b) && (b != A(address(0x0))))
            state2 = false;
    }

    function h() public returns (bool) {
        if (!(state || state2))
            assert(false); // test::coverage
        else
            return true; // test::coverage
    }
}

// Some dummy contract
contract A {
    uint a = 42;
    uint b = 43;

    function f() public {
        a = a+1;
    }
}