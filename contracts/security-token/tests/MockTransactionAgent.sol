pragma solidity ^0.4.18;

import "../transactionAgent.sol";

contract MockTransactionAgent is transactionAgent {
  bool frozen = false;

  function MockTransactionAgent() {
    // This is here for our verification code only
  }

  function freeze() public {
    frozen = true;
  }

  function verify(address from, address to, uint256 value) public returns (uint256 newValue) {
    require(frozen == false);

    return 1;
  }
}
