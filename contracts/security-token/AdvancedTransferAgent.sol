pragma solidity ^0.4.18;

import "./KYCInterface.sol";
import "./RestrictedTransferAgent.sol";
import "zeppelin/contracts/ownership/Ownable.sol";

contract AdvancedTransferAgent is RestrictedTransferAgent, Ownable {
  mapping(address => bool) whitelist;
  mapping(address => bool) blacklist;

  event Whitelisted(address who, bool status);
  event Blacklisted(address who, bool status);
  event ChangedKYC(address newKYC);
  event BlacklistedAddress();

  function AdvancedTransferAgent(KYCInterface _KYC) RestrictedTransferAgent(_KYC) {
  }

  /**
   * @dev Setting the whitelist status for an address
   *
   * @param who Whose whitelist status will be changed
   * @param status True, if the address is whitelisted, false otherwise
   */
  function setWhitelist(address who, bool status) public onlyOwner {
    whitelist[who] = status;
    Whitelisted(who, status);
  }

  /**
   * @dev Setting KYC contract address
   *
   * @param _KYC Address of the new Know Your Customer contract
   */
  function setKYC(KYCInterface _KYC) public onlyOwner {
    KYC = _KYC;

    ChangedKYC(KYC);
  }

  /**
   * @dev Setting the blacklist status for an address
   *
   * @param who Whose blacklist status will be changed
   * @param status True, if the address is blacklisted, false otherwise
   */
  function setBlacklist(address who, bool status) public onlyOwner {
    blacklist[who] = status;
    Blacklisted(who, status);
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
    /* We invoke RestrictedTransferAgent here, because whatever it wants to do
       (like emit an event, KYC checks if KYC is specified), we want to do too. */
    if (blacklist[from] || blacklist[to]) {
      BlacklistedAddress();
      return 0;
    } else {
      if (whitelist[from] || whitelist[to]) {
        return UnrestrictedTransferAgent.verify(from, to, value);
      } else {
        return RestrictedTransferAgent.verify(from, to, value);
      }
    }
  }
}
