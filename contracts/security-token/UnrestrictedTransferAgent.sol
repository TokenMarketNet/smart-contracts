pragma solidity ^0.4.18;

import "./SecurityTransferAgent.sol";

/** Transfer agent for a security token that does not limit transfers any way */
contract UnrestrictedTransferAgent is SecurityTransferAgent {

  function UnrestrictedTransferAgent() {
  }

  /**
   * @dev Checking if transfer can happen, and if so, what is the right amount
   *
   * @param from The account sending the tokens
   * @param to The account receiving the tokens
   * @param value The indended amount
   * @return The actual amount permitted
   */
  function verify(address from, address to, uint256 value) public view returns (uint256 newValue) {
    return value;
  }
}
