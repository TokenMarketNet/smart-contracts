/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.8;

import "./CrowdsaleBase.sol";

/**
 * A mixin that is selling tokens from a preallocated pool
 *
 * - Tokens have precreated supply "premined"
 *
 * - Token owner must transfer sellable tokens to the crowdsale contract using ERC20.approve()
 *
 * - The mixin does not implement buy entry point.
 *
 */
contract AllocatedCrowdsaleMixin is CrowdsaleBase {

  /* The party who holds the full token pool and has approve()'ed tokens for this crowdsale */
  address public beneficiary;

  /**
   * @param _beneficiary The account who has performed approve() to allocate tokens for the token sale.
   *
   */
  function AllocatedCrowdsaleMixin(address _beneficiary) {
    beneficiary = _beneficiary;
  }

  /**
   * Called from invest() to confirm if the curret investment does not break our cap rule.
   */
  function isBreakingCap(uint weiAmount, uint tokenAmount, uint weiRaisedTotal, uint tokensSoldTotal) constant returns (bool limitBroken) {
    if(tokenAmount > getTokensLeft()) {
      return true;
    } else {
      return false;
    }
  }

  /**
   * We are sold out when our approve pool becomes empty.
   */
  function isCrowdsaleFull() public constant returns (bool) {
    return getTokensLeft() == 0;
  }

  /**
   * Get the amount of unsold tokens allocated to this contract;
   */
  function getTokensLeft() public constant returns (uint) {
    return token.allowance(owner, this);
  }

  /**
   * Transfer tokens from approve() pool to the buyer.
   *
   * Use approve() given to this crowdsale to distribute the tokens.
   */
  function assignTokens(address receiver, uint tokenAmount) internal {
    if(!token.transferFrom(beneficiary, receiver, tokenAmount)) throw;
  }
}
