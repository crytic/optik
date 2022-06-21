pragma solidity ^0.7.1;


contract Reentrency {
    uint frames = 0;
    A a;

    function init(uint x) public {
        if (x*2  - 5 == 39) // x == 22
            if (a == A(address(0x0)))
                a = new A();
    }

    function enter(uint x, uint y) public {
        if (frames > 1)
            return;

        frames += 1;
        if (x*3 + 22 == 25) // x == 1
            if (a != A(address(0x0)))
                a.enter(address(this), x, y);
        frames -= 1;
    }

    function check() public returns (int) {
        if (frames == 2)
            return 0; // test::coverage
        else if (frames == 1)
            return -1; // test::coverage
        else
            return -2; // test::coverage
    }

}

// Some dummy contract
contract A {

    function enter(address c, uint x, uint y) public {
        uint key = 1000000;
        if (y+10 == key*10)
            Reentrency(c).check();
        else
            Reentrency(c).enter(x, y + key);
    }
}