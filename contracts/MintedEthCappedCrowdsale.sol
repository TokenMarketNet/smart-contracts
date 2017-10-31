/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.8;

import "./Crowdsale.sol";
import "./MintableToken.sol";

/**
 * ICO crowdsale contract that is capped by amout of ETH.
 *
 * - Tokens are dynamically created during the crowdsale
 *
 *
 */
contract MintedEthCappedCrowdsale is Crowdsale {

  /* Maximum amount of wei this crowdsale can raise. */
  uint public weiCap;

  function MintedEthCappedCrowdsale(address _token, PricingStrategy _pricingStrategy, address _multisigWallet, uint _start, uint _end, uint _minimumFundingGoal, uint _weiCap) Crowdsale(_token, _pricingStrategy, _multisigWallet, _start, _end, _minimumFundingGoal) {
    weiCap = _weiCap;
  }

  /**
   * Called from invest() to confirm if the curret investment does not break our cap rule.
   */
  function isBreakingCap(uint weiAmount, uint tokenAmount, uint weiRaisedTotal, uint tokensSoldTotal) constant returns (bool limitBroken) {
    return weiRaisedTotal > weiCap;
  }

  function isCrowdsaleFull() public constant returns (bool) {
    return weiRaised >= weiCap;
  }

  /**
   * Dynamically create tokens and assign them to the investor.
   */
  function assignTokens(address receiver, uint tokenAmount) internal {
    MintableToken mintableToken = MintableToken(token);
    mintableToken.mint(receiver, tokenAmount);
  }
}
