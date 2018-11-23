pragma solidity ^0.4.18;

interface ERC677Receiver {
  function tokenFallback(address from, uint256 amount, bytes data) returns (bool success);
}

interface ERC677 {
  event Transfer(address from, address receiver, uint256 amount, bytes data);
  function transferAndCall(ERC677Receiver receiver, uint amount, bytes data) returns (bool success);
}
