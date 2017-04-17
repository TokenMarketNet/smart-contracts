pragma solidity ^0.4.6;

/**
 * Interface for defining crowdsale pricing.
 */
contract PricingStrategy {

  /** Interface declaration. */
  function isPricingStrategy() public constant returns (bool) {
    return true;
  }

  /** Self check if all references are correctly set. */
  function isSane() public constant returns (bool) {
    return true;
  }

  /**
   * When somebody tries to buy tokens for X eth, calculate how many tokens they get.
   */
  function calculatePrice(uint value, uint tokensSold, uint weiRaised, address msgSender) public constant returns (uint tokenAmount);
}
