pragma solidity ^0.4.18;

interface transactionAgent {
  function verify(address from, address to, uint256 value) public returns (uint256 newValue);
}
