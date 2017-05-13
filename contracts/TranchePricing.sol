pragma solidity ^0.4.6;

import "./PricingStrategy.sol";
import "./Crowdsale.sol";
import "./SafeMathLib.sol";

/// @dev Tranche based pricing with special support for pre-ico deals.
contract TranchePricing is PricingStrategy {

  using SafeMathLib for uint;

  uint public constant MAX_TRANCHES = 10;

  // This is used for access control (defined as public for future uses)
  address public creator;

  // This contains all pre-ICO addresses, and their prices (weis per token)
  mapping (address => uint) public preicoAddresses;

  /**
  * Define pricing schedule using tranches.
  */
  struct Tranche {

      // Amount in weis when this tranche becomes active
      uint amount;

      // How many tokens per satoshi you will get while this tranche is active
      uint price;
  }

  // Store tranches in a fixed array, so that it can be seen in a blockchain explorer
  // Tranche 0 is always (0, 0)
  // (TODO: change this when we confirm dynamic arrays are explorable)
  Tranche[10] public tranches;

  // How many active tranches we have
  uint public trancheCount;

  /// @dev This modifier is used to check if the user is the creator
  modifier ifCreator {
    if(msg.sender != creator)
      throw;

    _;
  }

  /// @dev Contruction, creating a list of tranches
  /// @param _tranches uint[] tranches Pairs of (start amount, price)
  function TranchePricing(uint[] _tranches) {
    // Need to have tuples, length check
    if(_tranches.length % 2 == 1 || _tranches.length >= MAX_TRANCHES*2) {
      throw;
    }

    trancheCount = _tranches.length / 2;

    uint highestAmount = 0;

    for(uint i=0; i<_tranches.length/2; i++) {
      tranches[i].amount = _tranches[i*2];
      tranches[i].price = _tranches[i*2+1];

      // No invalid steps
      if((highestAmount != 0) && (tranches[i].amount <= highestAmount)) {
        throw;
      }

      highestAmount = tranches[i].amount;
    }

    // Last tranche price must be zero, terminating the crowdale
    if(tranches[trancheCount-1].price != 0) {
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

  /// @dev Iterate through tranches. You reach end of tranches when price = 0
  /// @return tuple (time, price)
  function getTranche(uint n) public constant returns (uint, uint) {
    return (tranches[n].amount, tranches[n].price);
  }

  function getFirstTranche() private constant returns (Tranche) {
    return tranches[0];
  }

  function getLastTranche() private constant returns (Tranche) {
    return tranches[trancheCount-1];
  }

  function getPricingStartsAt() public constant returns (uint) {
    return getFirstTranche().amount;
  }

  function getPricingEndsAt() public constant returns (uint) {
    return getLastTranche().amount;
  }

  function isSane(address _crowdsale) public constant returns(bool) {
    Crowdsale crowdsale = Crowdsale(_crowdsale);
    return crowdsale.startsAt() == getPricingStartsAt() && crowdsale.endsAt() == getPricingEndsAt();
  }

  /// @dev Get the current tranche or bail out if we are not in the tranche periods.
  /// @return {[type]} [description]
  function getCurrentTranche() private constant returns (Tranche) {
    uint i;

    for(i=0; i < tranches.length; i++) {
      if(now < tranches[i].amount) {
        return tranches[i-1];
      }
    }
  }

  /// @dev Get the current price.
  /// @return The current price or 0 if we are outside trache ranges
  function getCurrentPrice() public constant returns (uint result) {
    return getCurrentTranche().price;
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
