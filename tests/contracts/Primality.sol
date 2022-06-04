pragma solidity ^0.7.1;

contract Primality {

    uint256 public largePrime = 973013;
    uint256 private a = 0;
    
    function verifyPrime(uint256 x, uint256 y) external{
        require(x > 1 && x < largePrime);
        require(y > 1 && y < largePrime);
        if (x*y == largePrime){
            a = 1; // test::coverage
        }
    }
}
