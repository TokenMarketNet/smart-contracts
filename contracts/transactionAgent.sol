pragma solidity ^0.4.18;

contract transactionAgent {
  function verify(address from, address to, uint256 value) public returns (uint256 newValue);
}
