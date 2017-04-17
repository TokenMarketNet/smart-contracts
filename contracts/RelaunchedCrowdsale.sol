import "./MintedTokenCappedCrowdsale.sol";


contract RelaunchedCrowdsale is MintedTokenCappedCrowdsale {

  function RelaunchedCrowdsale(address _token, PricingStrategy _pricingStrategy, address _multisigWallet, uint _start, uint _end, uint _minimumFundingGoal, uint _maximumSellableTokens) MintedTokenCappedCrowdsale(_token, _pricingStrategy, _multisigWallet, _start, _end, _minimumFundingGoal, _maximumSellableTokens) {

  }

  /**
   * Rebuild invest data back to the crowdsale.
   */
  function setInvestData(address addr, uint weiAmount, uint tokenAmount) onlyOwner public {
    investedAmountOf[addr] = weiAmount;
    tokenAmountOf[addr] = tokenAmount;
    Invested(addr, weiAmount, tokenAmount);
  }


}