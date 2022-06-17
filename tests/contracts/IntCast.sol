contract IntCast {
    int256 n = 0;

    function f(uint256 newn) public {
        n = int256(newn);
    }

    function g() public {
        if ((n - 256) == -31)
            n = 0; // test::coverage
    }
}