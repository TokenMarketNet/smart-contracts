pragma solidity ^0.4.6;

import "./PricingStrategy.sol";

/**
 * Fixed crowdsale pricing - everybody gets the same price.
 */
contract FlatPricing is PricingStrategy {

  uint public tokenPrice;

  function FlatPricing(uint _tokenPrice) {
    tokenPrice = _tokenPrice;
  }

  /**
   * Calculate the current price for buy in amount.
   *
   * @param  {uint amount} Buy-in value in wei.
   */
  function calculatePrice(uint value, uint tokensSold, uint weiRaised) public constant returns (uint) {
    return value / tokenPrice;
  }

}
