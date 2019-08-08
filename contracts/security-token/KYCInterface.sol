pragma solidity ^0.4.18;

interface KYCInterface {
  event FlagsSet(address indexed who, uint256 indexed flags);

  function getFlag(address addr, uint8 flag) external view returns (bool);
}
