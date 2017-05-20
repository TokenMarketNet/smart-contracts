pragma solidity ^0.4.6;

import "./PricingStrategy.sol";
import "./SafeMathLib.sol";

/**
 * Fixed crowdsale pricing - everybody gets the same price.
 */
contract FlatPricing is PricingStrategy {

  using SafeMathLib for uint;

  /* How many weis one token costs */
  uint public tokenPrice;

  function FlatPricing(uint _tokenPrice) {
    tokenPrice = _tokenPrice;
  }

  /**
   * Calculate the current price for buy in amount.
   *
   * @param  {uint amount} Buy-in value in wei.
   */
  function calculatePrice(uint value, uint weiRaised, uint tokensSold, address msgSender, uint decimals) public constant returns (uint) {
    uint multiplier = 10 ** decimals;
    return value.times(multiplier) / tokenPrice;
  }

}
