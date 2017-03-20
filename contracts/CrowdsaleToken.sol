pragma solidity ^0.4.8;

import "zeppelin/contracts/token/StandardToken.sol";
import "./UpgradeAgentEnabledToken.sol";
import "./ReleasableToken.sol";
import "./MintableToken.sol";
import "./SafeMathLib.sol";


/**
 * A crowdsaled token.
 *
 * An ERC-20 token designed specifically for crowdsales with investor protection and further development path.
 *
 * - The token transfer() is disabled until the crowdsale is over
 * - The token contract gives an opt-in upgrade path to a new contract
 * - The same token can be part of several crowdsales through approve() mechanism
 * - The token can be capped (supply set in the constructor) or uncapped (crowdsale contract can mint new tokens)
 *
 */
contract CrowdsaleToken is ReleasableToken, MintableToken, UpgradeAgentEnabledToken {

  string public name;

  string public symbol;

  /** We don't want to support decimal places as it's not very well handled by different wallets */
  uint public decimals = 0;

  /**
   * Construct the token.
   *
   * This token must be created through a team multisig wallet, so that it is owned by that wallet.
   */
  function CrowdsaleToken(string _name, string _symbol, uint _initialSupply) {

    // Create from team multisig
    owner = msg.sender;
    upgradeMaster = msg.sender;

    name = _name;
    symbol = _symbol;

    totalSupply = _initialSupply;

    // Create initially all balance on the team multisig
    balances[msg.sender] = totalSupply;
  }


  /**
   * Allow upgrade agent functionality kick in only if the crowdsale was success.
   */
  modifier canUpgrade() {
    if(!released) throw;
    _;
  }

}
