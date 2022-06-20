pragma solidity ^0.7.1;

// The sequence we look for is:
// f1(), g(address_of_a, val) with val % 123456 == 3
// f2(), g(address_of_b, val2) with val2 % 123456 == 3
// h()

contract MessageCall {
    bool state = true;
    bool state2 = true;
    A a;
    A b;

    function f1() public {
        if (a == A(address(0x0)))
            a = new A(0xaaaaaaa);
    }

    function f2() public {
        if (b == A(address(0x0)))
            b = new A(0xbbbbbbbb);
    }

    function g(address x, uint val) public {
        if (A(x) == a)
            a.f(val);
        if ((A(x) == b) && (b != A(address(0x0))))
            b.f(val);
    }

    function h() public returns (bool) {
        if (a != A(address(0)) && b != A(address(0)))
            if (a.g() == b.g())
                return false; // test::coverage
        return true;
    }
}

// Some dummy contract
contract A {
    uint a = 123456;
    uint key;

    constructor (uint k) {
        key = k;
    }
    
    function f(uint x) public {
        if (x%a == 3)
            a = 0;
    }

    function g() public returns (uint) {
        if (a == 0)
            return 22;
        else
            return key;
    }
}