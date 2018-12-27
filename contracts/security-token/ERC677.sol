pragma solidity ^0.4.18;

interface ERC677Receiver {
  function tokenFallback(address from, uint256 amount, bytes data) returns (bool success);
}

interface ERC677 {

  // TODO: Have a different event name to make sure that tools with bad APIs do not mix this with ERC-20 Transfer() event that lacks data parameter
  event ERC677Transfer(address from, address receiver, uint256 amount, bytes data);

  function transferAndCall(ERC677Receiver receiver, uint amount, bytes data) returns (bool success);
}
