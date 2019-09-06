/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.8;


import "./Recoverable.sol";
import "./SafeMathLib.sol";
import "./StandardTokenExt.sol";
import "zeppelin/contracts/ownership/Ownable.sol";

/**
 * Hold tokens for a group investor of investors until the unlock date.
 *
 * After the unlock date the investor can claim their tokens.
 *
 * Steps
 *
 * - Prepare a spreadsheet for token allocation
 * - Deploy this contract, with the sum to tokens to be distributed, from the owner account
 * - Call setInvestor for all investors from the owner account using a local script and CSV input
 * - Move tokensToBeAllocated in this contract using StandardToken.transfer()
 * - Call lock from the owner account
 * - Wait until the freeze period is over
 * - After the freeze time is over investors can call claim() from their address to get their tokens
 * - Tokens vest to the investors with individual schedules
 *
 */
contract TokenVault is Ownable, Recoverable {
  using SafeMathLib for uint;

  /** How many investors we have now */
  uint public investorCount;

  /** Sum from the spreadsheet how much tokens we should get on the contract. If the sum does not match at the time of the lock the vault is faulty and must be recreated.*/
  uint public tokensToBeAllocated;

  /** How many tokens investors have claimed so far */
  uint public totalClaimed;

  /** How many tokens our internal book keeping tells us to have at the time of lock() when all investor data has been loaded */
  uint public tokensAllocatedTotal;

  /** How much we have allocated to the investors invested */
  mapping(address => uint) public balances;

  /** How many tokens investors have claimed */
  mapping(address => uint) public claimed;

  /** When was the last claim by an investor **/
  mapping(address => uint) public lastClaimedAt;

  /** When our claim freeze is over (UNIX timestamp) - this is when the tokensPerSecond starts running */
  uint public freezeEndsAt;

  /** When this vault was locked (UNIX timestamp) */
  uint public lockedAt;

  /** defining the taps per account **/
  mapping(address => uint256) public tokensPerSecond;

  /** We can also define our own token, which will override the ICO one ***/
  StandardTokenExt public token;

  /** What is our current state.
   *
   * Loading: Investor data is being loaded and contract not yet locked
   * Holding: Holding tokens for investors
   * Distributing: Freeze time is over, investors can claim their tokens
   */
  enum State{Unknown, Loading, Holding, Distributing}

  /** We allocated tokens for investor */
  event Allocated(address investor, uint value);

  /** We distributed tokens to an investor */
  event Distributed(address investors, uint count);

  event Locked();

  /**
   * Create presale contract where lock up period is given days
   *
   * @param _owner Who can load investor data and lock
   * @param _freezeEndsAt UNIX timestamp when the vault unlocks
   * @param _token Token contract address we are distributing
   * @param _tokensToBeAllocated Total number of tokens this vault will hold - including decimal multiplication
   */
  function TokenVault(address _owner, uint _freezeEndsAt, StandardTokenExt _token, uint _tokensToBeAllocated) {

    owner = _owner;

    // Invalid owner
    if(owner == 0) {
      throw;
    }

    token = _token;

    // Check the address looks like a token contract
    if(!token.isToken()) {
      throw;
    }

    // Give argument
    if(_freezeEndsAt == 0) {
      throw;
    }

    // Sanity check on _tokensToBeAllocated
    if(_tokensToBeAllocated == 0) {
      throw;
    }

    if (_freezeEndsAt < now) {
      freezeEndsAt = now;
    } else {
      freezeEndsAt = _freezeEndsAt;
    }
    tokensToBeAllocated = _tokensToBeAllocated;
  }

  /**
   * @dev Add a participant to this Vault
   * @param investor Address of the participant who will be added to this vault
   * @param amount Amount of tokens this participant is entitled to in total
   * @param _tokensPerSecond Define the tap: how many tokens we permit the participant to withdraw per second, 0 to disable tap
   */
  function setInvestor(address investor, uint amount, uint _tokensPerSecond) public onlyOwner {

    if(lockedAt > 0) {
      // Cannot add new investors after the vault is locked
      throw;
    }

    if(amount == 0) throw; // No empty buys

    // Don't allow reset
    if(balances[investor] > 0) {
      throw;
    }

    balances[investor] = amount;

    investorCount++;

    tokensAllocatedTotal += amount;

    tokensPerSecond[investor] = _tokensPerSecond;

    Allocated(investor, amount);
  }

  /// @dev Lock the vault
  ///      - All balances have been loaded in correctly
  ///      - Tokens are transferred on this vault correctly
  ///      - Checks are in place to prevent creating a vault that is locked with incorrect token balances.
  function lock() onlyOwner {

    if(lockedAt > 0) {
      throw; // Already locked
    }

    // Spreadsheet sum does not match to what we have loaded to the investor data
    if(tokensAllocatedTotal != tokensToBeAllocated) {
      throw;
    }

    // Do not lock the vault if the given tokens are not on this contract
    if(token.balanceOf(address(this)) != tokensAllocatedTotal) {
      throw;
    }

    lockedAt = now;

    Locked();
  }

  /// @dev In the case locking failed, then allow the owner to reclaim the tokens on the contract.
  function recoverFailedLock() onlyOwner {
    if(lockedAt > 0) {
      throw;
    }

    // Transfer all tokens on this contract back to the owner
    token.transfer(owner, token.balanceOf(address(this)));
  }

  /// @dev Get the current balance of tokens in the vault
  /// @return uint How many tokens there are currently in vault
  function getBalance() public constant returns (uint howManyTokensCurrentlyInVault) {
    return token.balanceOf(address(this));
  }

  /// @dev How much the investor could claim based on the current time and his previous claims
  /// @param investor Address of the investor
  /// @return uint How many tokens the investor can claim now
  function getMaxClaimByNow(address investor) public constant returns (uint claimableAmount) {

    if (now < freezeEndsAt) {
      return 0;
    }

    uint previousClaimAt = lastClaimedAt[investor];

    // This investor has not claimed tokens yet.... start counting from the unfreeze time
    if (previousClaimAt == 0) {
      previousClaimAt = freezeEndsAt;
    }

    uint passed = now.minus(previousClaimAt);
    uint maxClaim = passed.times(tokensPerSecond[investor]);
    return maxClaim;
  }

  /// @dev Check how many tokens "investor" can claim, based on the previous claims and tokens left
  /// @param investor Address of the investor
  /// @return uint How many tokens the investor can claim now
  function getCurrentlyClaimableAmount(address investor) public constant returns (uint claimableAmount) {

    uint maxTokensLeft = balances[investor].minus(claimed[investor]);

    if (now < freezeEndsAt) {
      return 0;
    }

    uint maxClaim = getMaxClaimByNow(investor);

    if (tokensPerSecond[investor] > 0) {
      // This investor is vesting over time

      if (maxClaim > maxTokensLeft) {
        return maxTokensLeft;
      } else {
        return maxClaim;
      }
    } else {
      // This investor gets all tokens when the vault unlocks
      return maxTokensLeft;
    }
  }

  /// @dev Claim N bought tokens to the investor as the msg sender
  function claim() public {

    address investor = msg.sender;

    if(lockedAt == 0) {
      throw; // We were never locked
    }

    if(now < freezeEndsAt) {
      throw; // Trying to claim early
    }

    if(balances[investor] == 0) {
      // Not our investor
      throw;
    }

    uint amount = getCurrentlyClaimableAmount(investor);

    require(amount > 0); // This gives somewhat better user experience as running transactions with zero claim amounts might confuse users

    // Update when and how much tokens the investor has claimed
    lastClaimedAt[investor] = now;
    claimed[investor] += amount;

    // Update our bean counter
    totalClaimed += amount;

    // Send tokens to the investors
    token.transfer(investor, amount);
    Distributed(investor, amount);
  }

  /// @dev This function is prototyped in Recoverable contract
  function tokensToBeReturned(ERC20Basic tokenToClaim) public returns (uint) {
    if (address(tokenToClaim) == address(token)) {
      return getBalance().minus(tokensAllocatedTotal.minus(totalClaimed));
    } else {
      return tokenToClaim.balanceOf(this);
    }
  }

  /// @dev Resolve the contract umambigious state
  function getState() public constant returns(State) {
    if(lockedAt == 0) {
      return State.Loading;
    } else if(now > freezeEndsAt) {
      return State.Distributing;
    } else {
      return State.Holding;
    }
  }

}
