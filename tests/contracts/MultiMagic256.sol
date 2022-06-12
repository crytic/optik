// A version of MultiMagic that uses uint instead of bool
// to force each flag to live in a separate storage slot

pragma solidity ^0.7.1;

contract MultiMagic256
{
  uint256 flag_1 = 0;
  uint256 flag_2 = 0;
  uint256 values_found = 0;

  function set_flag_1(uint magic_1, uint magic_2, uint magic_3) public {
    require(magic_1 == 42);
    require(magic_2*2 == magic_3+129);
    flag_1 = 1;
  }

  function set_flag_2(uint magic_1, uint magic_2) public {
     require(flag_1 == 1);
     require(magic_1 +3 == magic_2 * 456);
     flag_2 = 1;
  }

  function check_flags() public {
      require(flag_1 == 1);
      require(flag_2 == 1);
      values_found = 1; // test::coverage
  }

}