pragma solidity ^0.4.18;

import "./KYCInterface.sol";
import "./UnrestrictedTransferAgent.sol";

contract RestrictedTransferAgent is UnrestrictedTransferAgent {

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
  function verify(address from, address to, uint256 value) public returns (uint256 newValue) {
    if (address(KYC) == address(0)) {
      return value;
    }

    if (KYC.isWhitelisted(to)) {
      /* We invoke UnrestrictedTransferAgent here, because whatever it wants to do
         (like emit an event), we want to do too. */
      return super.verify(from, to, value);
    } else {
      return 0;
    }
  }
}
