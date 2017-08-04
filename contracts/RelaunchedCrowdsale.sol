/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.8;

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
  event RestoredInvestment(address addr, uint originalTxHash);

  mapping(uint => bool) public reissuedTransactions;

  function RelaunchedCrowdsale(address _token, PricingStrategy _pricingStrategy, address _multisigWallet, uint _start, uint _end, uint _minimumFundingGoal, uint _maximumSellableTokens) MintedTokenCappedCrowdsale(_token, _pricingStrategy, _multisigWallet, _start, _end, _minimumFundingGoal, _maximumSellableTokens) {
  }

  /**
   * Check if a particular transaction has already been written.
   */
  function getRestoredTransactionStatus(uint _originalTxHash) public constant returns(bool) {
    return reissuedTransactions[_originalTxHash];
  }

  /**
   * Rebuild the previous invest data back to the crowdsale.
   */
  function setInvestorData(address _addr, uint _weiAmount, uint _tokenAmount, uint _originalTxHash) onlyOwner public {

    if(investedAmountOf[_addr] == 0) {
      investorCount++;
    }

    investedAmountOf[_addr] += _weiAmount;
    tokenAmountOf[_addr] += _tokenAmount;

    weiRaised += _weiAmount;
    tokensSold += _tokenAmount;

    Invested(_addr, _weiAmount, _tokenAmount, 0);
    RestoredInvestment(_addr, _originalTxHash);
  }

  /**
   * Rebuild the previous invest data and do a token reissuance.
   */
  function setInvestorDataAndIssueNewToken(address _addr, uint _weiAmount, uint _tokenAmount, uint _originalTxHash) onlyOwner public {

    // This transaction has already been rebuild
    if(reissuedTransactions[_originalTxHash]) {
      throw;
    }

    setInvestorData(_addr, _weiAmount, _tokenAmount, _originalTxHash);

    // Check that we did not bust the cap in the restoration process
    if(isBreakingCap(_weiAmount, _tokenAmount, weiRaised, tokensSold)) {
      throw;
    }

    // Mark transaction processed
    reissuedTransactions[_originalTxHash] = true;

    // Mint new token to give it to the original investor
    MintableToken mintableToken = MintableToken(token);
    mintableToken.mint(_addr, _tokenAmount);
  }

}
