pragma solidity ^0.7.1;

contract MultiMagic
{
  bool flag_1 = false;
  bool flag_2 = false;
  bool values_found = false;

  function set_flag_1(uint magic_1, uint magic_2, uint magic_3) public {
    require(magic_1 == 42);
    require(magic_2*2 == magic_3+129);
    flag_1 = true;
  }

  function set_flag_2(uint magic_1, uint magic_2) public {
     require(flag_1);
     require(magic_1 +3 == magic_2 * 456);
     flag_2 = true;
  }

  function check_flags() public {
      require(flag_1);
      require(flag_2);
      values_found = true; // test::coverage
  }

}