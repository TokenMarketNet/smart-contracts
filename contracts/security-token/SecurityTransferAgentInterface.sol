pragma solidity ^0.4.18;

interface SecurityTransferAgent {
  function verify(address from, address to, uint256 value) external view returns (uint256 newValue);
}
