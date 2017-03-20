pragma solidity ^0.4.6;

/**
 * Interface for defining crowdsale pricing.
 */
contract PricingStrategy {

  function calculatePrice(uint value, uint tokensSold, uint weiRaised) public constant returns (uint);
}
