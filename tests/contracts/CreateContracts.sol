pragma solidity ^0.7.1;

// Contract to test
contract CreateContracts {
    bool state = false;
    bool state2 = false;
    A a;
    A b;

    constructor (){
        a = new A(468745);
        b = new A(9894565814);
    }

    function f(address x, uint guess1, uint guess2) public {
        if (A(x) == a){
            state = a.check(guess1);
            if (state)
                state2 = b.check(guess2);
        }
    }

    function g() public returns (bool) {
        if (!(state || state2))
            return false; // test::coverage
        else
            return true; // test::coverage
    }
}

// Some dummy contract
contract A {
    uint key;

    constructor (uint k){
        key = k;
    }

    function check(uint val) public returns (bool) {
        return (val % key == 22);
    }
}