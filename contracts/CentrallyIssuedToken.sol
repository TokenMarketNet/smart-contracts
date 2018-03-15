pragma solidity ^0.4.6;

import "./BurnableToken.sol";
import "./UpgradeableToken.sol";


/**
 * Centrally issued Ethereum token.
 *
 * We mix in burnable and upgradeable traits.
 *
 * Token supply is created in the token contract creation and allocated to owner.
 * The owner can then transfer from its supply to crowdsale participants.
 * The owner, or anybody, can burn any excessive tokens they are holding.
 *
 */
contract CentrallyIssuedToken is BurnableToken, UpgradeableToken {

  // Token meta information
  string public name;
  string public symbol;
  uint public decimals;

  // Token release switch
  bool public released = false;

  // The date before the release must be finalized or upgrade path will be forced
  uint public releaseFinalizationDate;

  /** Name and symbol were updated. */
  event UpdatedTokenInformation(string newName, string newSymbol);

  function CentrallyIssuedToken(address _owner, string _name, string _symbol, uint _totalSupply, uint _decimals, uint _releaseFinalizationDate)  UpgradeableToken(_owner) {
    name = _name;
    symbol = _symbol;
    totalSupply_ = _totalSupply;
    decimals = _decimals;

    // Allocate initial balance to the owner
    balances[_owner] = _totalSupply;

    releaseFinalizationDate = _releaseFinalizationDate;
  }

  /**
   * Owner can update token information here.
   *
   * It is often useful to conceal the actual token association, until
   * the token operations, like central issuance or reissuance have been completed.
   * In this case the initial token can be supplied with empty name and symbol information.
   *
   * This function allows the token owner to rename the token after the operations
   * have been completed and then point the audience to use the token contract.
   */
  function setTokenInformation(string _name, string _symbol) {

    if(msg.sender != upgradeMaster) {
      throw;
    }

    name = _name;
    symbol = _symbol;
    UpdatedTokenInformation(name, symbol);
  }


  /**
   * Kill switch for the token in the case of distribution issue.
   *
   */
  function transfer(address _to, uint _value) returns (bool success) {

    if(now > releaseFinalizationDate) {
      if(!released) {
        throw;
      }
    }

    return super.transfer(_to, _value);
  }

  /**
   * One way function to perform the final token release.
   */
  function releaseTokenTransfer() {
    if(msg.sender != upgradeMaster) {
      throw;
    }

    released = true;
  }
}
