pragma solidity ^0.4.0;

import "./CrowdsaleBase.sol";

contract StartableCrowdsale is CrowdsaleBase{

  event StartAtChanged(uint newStartAt);


  constructor  (address _token, PricingStrategy _pricingStrategy, address _multisigWallet, uint _start, uint _end, uint _minimumFundingGoal)
  CrowdsaleBase (_token, _pricingStrategy, _multisigWallet, _start, _end, _minimumFundingGoal) public{}


  /**
  * @dev Start Crowdsale
  */
  function startCrowdsale () public onlyOwner inState(State.PreFunding){
    startsAt = now;
    StartAtChanged(startsAt);

  }
}
