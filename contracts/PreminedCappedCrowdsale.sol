
pragma solidity ^0.4.8;

import "./Crowdsale.sol";

/**
 * PreICO crowdsale contract.
 *
 *
 * Intended usage
 *
 * - Tokens have precreated supply "premined"
 * - Small share of tokens of the actual crowdsale
 * - A short time window
 * - Flat price
 * - beneficiary is the party who is supplying the tokens for this ICO
 *
 */
contract PreminedCappedCrowdsale is Crowdsale {

  /** How many ETH in max we are allowed to raise */
  uint public weiCap;

  /* The party who holds the full token pool and has approve()'ed tokens for this crowdsale */
  address public beneficiary;

  function PreminedCappedCrowdsale(address _token, PricingStrategy _pricingStrategy, address _multisigWallet, uint _start, uint _end, uint _minimumFundingGoal, uint _weiCap, address _beneficiary) Crowdsale(_token, _pricingStrategy, _multisigWallet, _start, _end, _minimumFundingGoal) {
    weiCap = _weiCap;
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

  function isCrowdsaleFull() public constant returns (bool) {
    return getTokensLeft() == 0;
  }

  /**
   * Get the amount of unsold tokens allocated to this contract;
   */
  function getTokensLeft() public constant returns (uint) {
    return token.allowance(owner, this);
  }

  function assignTokens(address receiver, uint tokenAmount) private {
    // Use approve() given to this crowdsale to distribute the tokens
    if(!token.transferFrom(beneficiary, receiver, tokenAmount)) throw;
  }
}
