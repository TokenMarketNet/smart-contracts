pragma solidity ^0.4.18;

import "../ERC677.sol";

contract MockERC677Receiver is ERC677Receiver {
  function tokenFallback(address from, uint256 amount, bytes data) returns (bool success) {
    return true;
  }
}
