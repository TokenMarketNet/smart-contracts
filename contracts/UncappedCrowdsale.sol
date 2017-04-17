pragma solidity ^0.4.8;

import "./Crowdsale.sol";
import "./MintableToken.sol";


/**
 * Uncapped ICO crowdsale contract.
 *
 *
 * Intended usage
 *
 * - A short time window
 * - Flat price
 * - No cap
 *
 */
contract UncappedCrowdsale is Crowdsale {

  function UncappedCrowdsale(address _token, PricingStrategy _pricingStrategy, address _multisigWallet, uint _start, uint _end, uint _minimumFundingGoal) Crowdsale(_token, _pricingStrategy, _multisigWallet, _start, _end, _minimumFundingGoal) {

  }

  /**
   * Called from invest() to confirm if the curret investment does not break our cap rule.
   */
  function isBreakingCap(uint weiAmount, uint tokenAmount, uint weiRaisedTotal, uint tokensSoldTotal) constant returns (bool limitBroken) {
    return false;
  }

  function isCrowdsaleFull() public constant returns (bool) {
    // Uncle Scrooge
    return false;
  }

  function assignTokens(address receiver, uint tokenAmount) private {
    MintableToken mintableToken = MintableToken(token);
    mintableToken.mint(receiver, tokenAmount);
  }
}
