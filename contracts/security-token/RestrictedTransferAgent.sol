pragma solidity ^0.4.18;

import "./KYCInterface.sol";
import "./SecurityTransferAgentInterface.sol";

contract RestrictedTransferAgent is SecurityTransferAgent {
  KYCInterface KYC;

  function RestrictedTransferAgent(KYCInterface _KYC) {
    KYC = _KYC;
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
    if (address(KYC) == address(0)) {
      return value;
    }

    // The following ifs might seem counterintuitive, but this function will
    // be executed upon every transfer, so we want to make sure that despite of
    // Solidity's optimization settings, only relevant external calls are made
    if (KYC.getFlag(to, 0)) {
      if (KYC.getFlag(from, 0)) {
        return value;
      } else {
        return 0;
      }
    } else if (KYC.getFlag(from, 1)) {
      return value;
    } else {
      return 0;
    }
  }
}
