import "./MintedTokenCappedCrowdsale.sol";


contract RelaunchedCrowdsale is MintedTokenCappedCrowdsale {

  function RelaunchedCrowdsale(address _token, PricingStrategy _pricingStrategy, address _multisigWallet, uint _start, uint _end, uint _minimumFundingGoal, uint _maximumSellableTokens) MintedTokenCappedCrowdsale(_token, _pricingStrategy, _multisigWallet, _start, _end, _minimumFundingGoal, _maximumSellableTokens) {

  }

  /**
   * Rebuild invest data back to the crowdsale.
   */
  function setInvestorData(address _addr, uint _weiAmount, uint _tokenAmount) onlyOwner public {
    investedAmountOf[_addr] = _weiAmount;
    tokenAmountOf[_addr] = _tokenAmount;
    weiRaised += _weiAmount;
    tokensSold += _tokenAmount;
    investorCount++;
    Invested(_addr, _weiAmount, _tokenAmount);
  }


}