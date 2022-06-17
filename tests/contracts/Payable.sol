pragma solidity ^0.7.1;

contract Payable {

  uint state = 0;
  uint another_state = 0;

  function x() public payable {
    if (msg.value*2 +1 == 129)
        state = msg.value; // test::coverage
  }

  function a(uint) public {
    another_state = 1;
  }

  function b() public returns (bool) {
    return(state == 0);
  }
}