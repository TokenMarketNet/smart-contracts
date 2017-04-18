import "./MintedTokenCappedCrowdsale.sol";


/**
 * A crowdsale that retains the previous token, but changes some parameters.
 *
 * Investor data can be manually fed in.
 *
 * Mostly useful as a hot fix.
 *
 */
contract RelaunchedCrowdsale is MintedTokenCappedCrowdsale {

  // This transaction was restored from a previous crowdsale
  event RestoredInvestment(address addr, uint256 weiAmount, uint256 tokenAmount, uint originalTxHash);

  function RelaunchedCrowdsale(address _token, PricingStrategy _pricingStrategy, address _multisigWallet, uint _start, uint _end, uint _minimumFundingGoal, uint _maximumSellableTokens) MintedTokenCappedCrowdsale(_token, _pricingStrategy, _multisigWallet, _start, _end, _minimumFundingGoal, _maximumSellableTokens) {

  }

  /**
   * Rebuild the previous invest data back to the crowdsale.
   */
  function setInvestorData(address _addr, uint _weiAmount, uint _tokenAmount, uint _originalTxHash) onlyOwner public {

    investedAmountOf[_addr] = _weiAmount;
    tokenAmountOf[_addr] = _tokenAmount;

    weiRaised += _weiAmount;
    tokensSold += _tokenAmount;
    investorCount++;

    Invested(_addr, _weiAmount, _tokenAmount);
    RestoredInvestment(_addr, _weiAmount, _tokenAmount, _originalTxHash);
  }

  /**
   * Rebuild the previous invest data and do a token reissuance.
   */
  function setInvestorDataAndIssueNewToken(address _addr, uint _weiAmount, uint _tokenAmount, uint _originalTxHash) onlyOwner public {

    setInvestorData(_addr, _weiAmount, _tokenAmount, _originalTxHash);

    // Check that we did not bust the cap
    if(isBreakingCap(_tokenAmount, _weiAmount, weiRaised, tokensSold)) {
      throw;
    }

    // Mint new token to give it to the original investor
    MintableToken mintableToken = MintableToken(token);
    mintableToken.mint(_addr, _tokenAmount);
  }

}
