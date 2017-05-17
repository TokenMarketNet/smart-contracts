
pragma solidity ^0.4.8;

import "./Crowdsale.sol";

/**
 * A crowdsale that is selling tokens from a preallocated pool
 *
 *
 * - Tokens have precreated supply "premined"
 *
 * - Token owner must transfer sellable tokens to the crowdsale contract using ERC20.approve()
 *
 */
contract AllocatedCrowdsale is Crowdsale {

  /* The party who holds the full token pool and has approve()'ed tokens for this crowdsale */
  address public beneficiary;

  function AllocatedCrowdsale(address _token, PricingStrategy _pricingStrategy, address _multisigWallet, uint _start, uint _end, uint _minimumFundingGoal, address _beneficiary) Crowdsale(_token, _pricingStrategy, _multisigWallet, _start, _end, _minimumFundingGoal) Crowdsale(_token, _pricingStrategy, _multisigWallet, _start, _end, _minimumFundingGoal) {
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
  function assignTokens(address receiver, uint tokenAmount) private {
    if(!token.transferFrom(beneficiary, receiver, tokenAmount)) throw;
  }
}
