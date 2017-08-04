/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.6;

import "./Crowdsale.sol";
import "./CrowdsaleToken.sol";
import "./SafeMathLib.sol";

/**
 * At the end of the successful crowdsale allocate % bonus of tokens to the team.
 *
 * Do not unlock the tokens.
 *
 * BonusAllocationFinal must be set as the minting agent for the MintableToken.
 *
 */
contract ExtraFinalizeAgent is FinalizeAgent {

  using SafeMathLib for uint;

  CrowdsaleToken public token;
  Crowdsale public crowdsale;

  /** Total percent of tokens minted to the team at the end of the sale as base points (0.0001) */
  uint public bonusBasePoints;

  /** Where we move the tokens at the end of the sale. */
  address public teamMultisig;

  /* How much bonus tokens we allocated */
  uint public allocatedBonus;

  /* How many tokens other finalizers will allocate and we do not count these in */
  uint public accountedTokenSales;

  function ExtraFinalizeAgent(CrowdsaleToken _token, Crowdsale _crowdsale, uint _bonusBasePoints, address _teamMultisig, uint _accountedTokenSales) {
    token = _token;
    crowdsale = _crowdsale;

    if(address(crowdsale) == 0) {
      throw;
    }

    teamMultisig = _teamMultisig;
    if(address(teamMultisig) == 0) {
      throw;
    }

    accountedTokenSales = _accountedTokenSales;
  }

  /* Can we run finalize properly */
  function isSane() public constant returns (bool) {
    return (token.mintAgents(address(this)) == true);
  }

  /** Called once by crowdsale finalize() if the sale was success. */
  function finalizeCrowdsale() {
    if(msg.sender != address(crowdsale)) {
      throw;
    }

    // How many % of tokens the founders and others get
    uint tokensSold = crowdsale.tokensSold().minus(accountedTokenSales);
    allocatedBonus = tokensSold.times(bonusBasePoints) / 10000;

    // move tokens to the team multisig wallet
    token.mint(teamMultisig, allocatedBonus);

  }

}
