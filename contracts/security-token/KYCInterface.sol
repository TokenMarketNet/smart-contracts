pragma solidity ^0.4.18;

import "./KYCAttributes.sol";

interface KYCInterface {
  event AttributesSet(address indexed who, uint256 indexed attributes);

  function getAttribute(address addr, KYCAttributes.KYCAttribute attribute) external view returns (bool);
}
