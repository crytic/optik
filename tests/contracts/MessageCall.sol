pragma solidity ^0.7.1;

contract MessageCall {
    bool state = false;
    A a;
    A b;

    function f(address x, uint val, uint val2, uint val3, uint val4) public {
        if (a == A(address(0x0)))
            a = new A(0xaaaaaaa);
        if (b == A(address(0x0)))
            b = new A(0xbbbbbbbb);

        if (A(x) == a)
            if (a.f(val))
                if (b.f(val2))
                    if (val3 != val4)
                    {
                        if (a.g(val3) == b.g(val4))
                            state = true; // test::coverage
                        else
                            state = false; // test::coverage
                    }
    }
}

// Some dummy contract
contract A {
    uint key;

    constructor (uint k) {
        key = k;
    }

    function f(uint x) public returns (bool) {
        return (x*2  +154  == 354);
    }

    function g(uint val) public returns (uint) {
        return (val & key);
    }
}