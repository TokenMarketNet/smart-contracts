pragma solidity ^0.4.18;

import "./KYCAttributes.sol";
import "./KYCInterface.sol";
import "./SecurityTransferAgentInterface.sol";

contract RestrictedTransferAgent is SecurityTransferAgent, KYCAttributes {
  KYCInterface KYC;

  function RestrictedTransferAgent(KYCInterface _KYC) {
    KYC = _KYC;
  }

  /**
   * @dev Checking if transfer can happen, and if so, what is the right amount
   *
   * @param from The account sending the tokens
   * @param to The account receiving the tokens
   * @param value The intended amount
   * @return The actual amount permitted
   */
  function verify(address from, address to, uint256 value) public view returns (uint256 newValue) {
    if (address(KYC) == address(0)) {
      return value;
    }

    if (KYC.getAttribute(to, KYCAttribute.KYCCleared) && KYC.getAttribute(from, KYCAttribute.KYCCleared)) {
      return value;
    } else if (KYC.getAttribute(from, KYCAttribute.CanPushTokens)) {
      return value;
    } else {
      revert("Token transaction not permitted");
    }
  }
}
