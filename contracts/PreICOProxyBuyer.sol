/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.6;

import "zeppelin/contracts/math/SafeMath.sol";
import "./Crowdsale.sol";
import "./Haltable.sol";

/**
 * Collect funds from presale investors, buy tokens for them in a single transaction and distribute out tokens.
 *
 * - Collect funds from pre-sale investors
 * - Send funds to the crowdsale when it opens
 * - Allow owner to set the crowdsale
 * - Have refund after X days as a safety hatch if the crowdsale doesn't materilize
 * - Allow unlimited investors
 * - Tokens are distributed on PreICOProxyBuyer smart contract first
 * - The original investors can claim their tokens from the smart contract after the token transfer has been released
 * - All functions can be halted by owner if something goes wrong
 *
 */
contract PreICOProxyBuyer is Ownable, Haltable {
  using SafeMath for uint;

  /** How many investors we have now */
  uint public investorCount;

  /** How many wei we have raised totla. */
  uint public weiRaised;

  /** Who are our investors (iterable) */
  address[] public investors;

  /** How much they have invested */
  mapping(address => uint) public balances;

  /** How many tokens investors have claimed */
  mapping(address => uint) public claimed;

  /** When our refund freeze is over (UNIT timestamp) */
  uint public freezeEndsAt;

  /** What is the minimum buy in */
  uint public weiMinimumLimit;

  /** What is the maximum buy in */
  uint public weiMaximumLimit;

  /** How many weis total we are allowed to collect. */
  uint public weiCap;

  /** How many tokens were bought */
  uint public tokensBought;

   /** How many investors have claimed their tokens */
  uint public claimCount;

  uint public totalClaimed;

  /** If timeLock > 0, claiming is possible only after the time has passed **/
  uint public timeLock;

  /** This is used to signal that we want the refund **/
  bool public forcedRefund;

  /** Our ICO contract where we will move the funds */
  Crowdsale public crowdsale;

  /** What is our current state. */
  enum State{Unknown, Funding, Distributing, Refunding}

  /** Somebody loaded their investment money */
  event Invested(address investor, uint weiAmount, uint tokenAmount, uint128 customerId);

  /** Refund claimed */
  event Refunded(address investor, uint value);

  /** We executed our buy */
  event TokensBoughts(uint count);

  /** We distributed tokens to an investor */
  event Distributed(address investor, uint count);

  /**
   * Create presale contract where lock up period is given days
   */
  function PreICOProxyBuyer(address _owner, uint _freezeEndsAt, uint _weiMinimumLimit, uint _weiMaximumLimit, uint _weiCap) {

    owner = _owner;

    // Give argument
    if(_freezeEndsAt == 0) {
      throw;
    }

    // Give argument
    if(_weiMinimumLimit == 0) {
      throw;
    }

    if(_weiMaximumLimit == 0) {
      throw;
    }

    weiMinimumLimit = _weiMinimumLimit;
    weiMaximumLimit = _weiMaximumLimit;
    weiCap = _weiCap;
    freezeEndsAt = _freezeEndsAt;
  }

  /**
   * Get the token we are distributing.
   */
  function getToken() public constant returns(FractionalERC20) {
    if(address(crowdsale) == 0)  {
      throw;
    }

    return crowdsale.token();
  }

  /**
   * Participate to a presale.
   */
  function invest(uint128 customerId) private {

    // Cannot invest anymore through crowdsale when moving has begun
    if(getState() != State.Funding) throw;

    if(msg.value == 0) throw; // No empty buys

    address investor = msg.sender;

    bool existing = balances[investor] > 0;

    balances[investor] = balances[investor].add(msg.value);

    // Need to satisfy minimum and maximum limits
    if(balances[investor] < weiMinimumLimit || balances[investor] > weiMaximumLimit) {
      throw;
    }

    // This is a new investor
    if(!existing) {
      investors.push(investor);
      investorCount++;
    }

    weiRaised = weiRaised.add(msg.value);
    if(weiRaised > weiCap) {
      throw;
    }

    // We will use the same event form the Crowdsale for compatibility reasons
    // despite not having a token amount.
    Invested(investor, msg.value, 0, customerId);
  }

  function buyWithCustomerId(uint128 customerId) public stopInEmergency payable {
    invest(customerId);
  }

  function buy() public stopInEmergency payable {
    invest(0x0);
  }


  /**
   * Load funds to the crowdsale for all investors.
   *
   *
   */
  function buyForEverybody() stopNonOwnersInEmergency public {

    if(getState() != State.Funding) {
      // Only allow buy once
      throw;
    }

    // Crowdsale not yet set
    if(address(crowdsale) == 0) throw;

    // Buy tokens on the contract
    crowdsale.invest.value(weiRaised)(address(this));

    // Record how many tokens we got
    tokensBought = getToken().balanceOf(address(this));

    if(tokensBought == 0) {
      // Did not get any tokens
      throw;
    }

    TokensBoughts(tokensBought);
  }

  /**
   * How may tokens each investor gets.
   */
  function getClaimAmount(address investor) public constant returns (uint) {

    // Claims can be only made if we manage to buy tokens
    if(getState() != State.Distributing) {
      throw;
    }
    return balances[investor].mul(tokensBought) / weiRaised;
  }

  /**
   * How many tokens remain unclaimed for an investor.
   */
  function getClaimLeft(address investor) public constant returns (uint) {
    return getClaimAmount(investor).sub(claimed[investor]);
  }

  /**
   * Claim all remaining tokens for this investor.
   */
  function claimAll() {
    claim(getClaimLeft(msg.sender));
  }

  /**
   * Claim N bought tokens to the investor as the msg sender.
   *
   */
  function claim(uint amount) stopInEmergency {
    require (now > timeLock);

    address investor = msg.sender;

    if(amount == 0) {
      throw;
    }

    if(getClaimLeft(investor) < amount) {
      // Woops we cannot get more than we have left
      throw;
    }

    // We track who many investor have (partially) claimed their tokens
    if(claimed[investor] == 0) {
      claimCount++;
    }

    claimed[investor] = claimed[investor].add(amount);
    totalClaimed = totalClaimed.add(amount);
    getToken().transfer(investor, amount);

    Distributed(investor, amount);
  }

  /**
   * ICO never happened. Allow refund.
   */
  function refund() stopInEmergency {

    // Trying to ask refund too soon
    if(getState() != State.Refunding) throw;

    address investor = msg.sender;
    if(balances[investor] == 0) throw;
    uint amount = balances[investor];
    delete balances[investor];
    if(!(investor.call.value(amount)())) throw;
    Refunded(investor, amount);
  }

  /**
   * Set the target crowdsale where we will move presale funds when the crowdsale opens.
   */
  function setCrowdsale(Crowdsale _crowdsale) public onlyOwner {
    crowdsale = _crowdsale;

    // Check interface
    if(!crowdsale.isCrowdsale()) true;
  }

  /// @dev Setting timelock (delay) for claiming
  /// @param _timeLock Time after which claiming is possible
  function setTimeLock(uint _timeLock) public onlyOwner {
    timeLock = _timeLock;
  }

  /// @dev This is used in the first case scenario, this will force the state
  ///      to refunding. This can be also used when the ICO fails to meet the cap.
  function forceRefund() public onlyOwner {
    forcedRefund = true;
  }

  /// @dev This should be used if the Crowdsale fails, to receive the refuld money.
  ///      we can't use Crowdsale's refund, since our default function does not
  ///      accept money in.
  function loadRefund() public payable {
    if(getState() != State.Refunding) throw;
  }

  /**
   * Resolve the contract umambigious state.
   */
  function getState() public returns(State) {
    if (forcedRefund)
      return State.Refunding;

    if(tokensBought == 0) {
      if(now >= freezeEndsAt) {
         return State.Refunding;
      } else {
        return State.Funding;
      }
    } else {
      return State.Distributing;
    }
  }

  /** Interface marker. */
  function isPresale() public constant returns (bool) {
    return true;
  }

  /** Explicitly call function from your wallet. */
  function() payable {
    throw;
  }
}
