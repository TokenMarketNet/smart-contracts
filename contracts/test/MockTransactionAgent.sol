pragma solidity ^0.4.18;

import "../transactionAgent.sol";

contract MockTransactionAgent is transactionAgent {
    function MockTransactionAgent() {
      // This is here for our verification code only
    }

    function verify(address from, address to, uint256 value) public returns (uint256 newValue) {
      return 1;
    }
}
