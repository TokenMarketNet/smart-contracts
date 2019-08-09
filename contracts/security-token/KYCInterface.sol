pragma solidity ^0.4.18;

interface KYCInterface {
  event AttributesSet(address indexed who, uint256 indexed flags);

  function getAttribute(address addr, uint8 attribute) external view returns (bool);
}
