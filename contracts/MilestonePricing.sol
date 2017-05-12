pragma solidity ^0.4.6;

import "./PricingStrategy.sol";
import "./Crowdsale.sol";
import "./SafeMathLib.sol";


/// @dev Time milestone based pricing with special support for pre-ico deals.
contract MilestonePricing is PricingStrategy {

  using SafeMathLib for uint;

  uint public constant MAX_MILESTONE = 10;

  // This is used for access control (defined as public for future uses)
  address public creator;

  // This contains all pre-ICO addresses, and their prices (weis per token)
  mapping (address => uint) public preicoAddresses;

  /**
  * Define pricing schedule using milestones.
  */
  struct Milestone {

      // UNIX timestamp when this milestone kicks in
      uint time;

      // How many tokens per satoshi you will get after this milestone has been passed
      uint price;
  }

  // Store milestones in a fixed array, so that it can be seen in a blockchain explorer
  // Milestone 0 is always (0, 0)
  // (TODO: change this when we confirm dynamic arrays are explorable)
  Milestone[10] public milestones;

  // How many active milestones we have
  uint public milestoneCount;

  /// @dev This modifier is used to check if the user is the creator
  modifier ifCreator {
    if(msg.sender != creator)
      throw;

    _;
  }

  /// @dev Contruction, creating a list of milestones
  /// @param _milestones uint[] milestones Pairs of (time, price)
  function MilestonePricing(uint[] _milestones) {
    // Need to have tuples, length check
    if(_milestones.length % 2 == 1 || _milestones.length >= MAX_MILESTONE*2) {
      throw;
    }

    milestoneCount = _milestones.length / 2;

    uint lastTimestamp = 0;

    for(uint i=0; i<_milestones.length/2; i++) {
      milestones[i].time = _milestones[i*2];
      milestones[i].price = _milestones[i*2+1];

      // No invalid steps
      if((lastTimestamp != 0) && (milestones[i].time <= lastTimestamp)) {
        throw;
      }

      lastTimestamp = milestones[i].time;
    }

    // Last milestone price must be zero, terminating the crowdale
    if(milestones[milestoneCount-1].price != 0) {
      throw;
    }

    // Implementing a simple access control using "creator"
    creator = msg.sender;
  }

  /// @dev This is invoked once for every pre-ICO address, set pricePerToken
  ///      to 0 to disable
  /// @param preicoAddress PresaleFundCollector address
  /// @param pricePerToken How many weis one token cost for pre-ico investors
  /// @return Result in boolean (true for sanity check)
  function addPreicoAddress(address preicoAddress, uint pricePerToken)
    public
    ifCreator
    returns (bool)
  {
    preicoAddresses[preicoAddress] = pricePerToken;

    return true; // Returning true, so other components know that this was sane
  }

  /// @dev Iterate through milestones. You reach end of milestones when price = 0
  /// @return tuple (time, price)
  function getMilestone(uint n) public constant returns (uint, uint) {
    return (milestones[n].time, milestones[n].price);
  }

  function getFirstMilestone() private constant returns (Milestone) {
    return milestones[0];
  }

  function getLastMilestone() private constant returns (Milestone) {
    return milestones[milestoneCount-1];
  }

  function getPricingStartsAt() public constant returns (uint) {
    return getFirstMilestone().time;
  }

  function getPricingEndsAt() public constant returns (uint) {
    return getLastMilestone().time;
  }

  function isSane(address _crowdsale) public constant returns(bool) {
    Crowdsale crowdsale = Crowdsale(_crowdsale);
    return crowdsale.startsAt() == getPricingStartsAt() && crowdsale.endsAt() == getPricingEndsAt();
  }

  /// @dev Get the current milestone or bail out if we are not in the milestone periods.
  /// @return {[type]} [description]
  function getCurrentMilestone() private constant returns (Milestone) {
    uint i;
    uint price;

    for(i=0; i<milestones.length; i++) {
      if(now < milestones[i].time) {
        return milestones[i-1];
      }
    }
  }

  /// @dev Get the current price.
  /// @return The current price or 0 if we are outside milestone period
  function getCurrentPrice() public constant returns (uint result) {
    return getCurrentMilestone().price;
  }

  /// @dev Calculate the current price for buy in amount.
  function calculatePrice(uint value, uint tokensSold, uint weiRaised, address msgSender, uint decimals) public constant returns (uint) {

    uint multiplier = 10 ** decimals;

    // This investor is coming through pre-ico
    if(preicoAddresses[msgSender] > 0) {
      return value.times(multiplier) / preicoAddresses[msgSender];
    }

    uint price = getCurrentPrice();
    return value.times(multiplier) / price;
  }

  function() payable {
    throw; // No money on this contract
  }

}
