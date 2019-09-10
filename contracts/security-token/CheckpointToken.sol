/**
 * This smart contract code is Copyright 2018, 2019 TokenMarket Ltd. For more information see https://tokenmarket.net
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 * NatSpec is used intentionally to cover also other than public functions.
 * Solidity 0.4.18 is intentionally used: it's stable, and our framework is
 * based on that.
 */

pragma solidity ^0.4.18;

import "./SecurityTransferAgentInterface.sol";
import "./ERC677Token.sol";
import "zeppelin/contracts/math/SafeMath.sol";

/**
 * @author TokenMarket /  Ville Sundell <ville at tokenmarket.net>
 *
 * The binary search was inspired by Jordi Baylina's MiniMeToken.
 */
contract CheckpointToken is ERC677Token {
  using SafeMath for uint256; // We use only uint256 for safety reasons (no boxing)

  /// @dev Name of the token, usually the company and/or series (like "TokenMeerkat Ltd. Series A"):
  string public name;
  /// @dev Ticker symbol, usually bases on the "name" above (like "MEER"):
  string public symbol;
  /// @dev Decimals are usually set to 18 for EIP-20 tokens:
  uint256 public decimals;
  /// @dev If transactionVerifier is set, that contract will be queried upon every token transaction:
  SecurityTransferAgent public transactionVerifier;

  /// @dev Checkpoint is the fundamental unit for our internal accounting
  ///      (who owns what, and at what moment in time)
  struct Checkpoint {
    uint256 checkpointID;
    uint256 value;
  }
  /// @dev This mapping contains checkpoints for every address:
  mapping (address => Checkpoint[]) public tokenBalances;
  /// @dev This is a one dimensional Checkpoint mapping of the overall token supply:
  Checkpoint[] public tokensTotal;
  /// @dev This contains current checkpoint ID, an incrementing integer,
  ///      incremented by the internal createCheckpoint() function.
  uint256 public currentCheckpointID;

  /// @dev This mapping keeps account for approve() -> fransferFrom() pattern:
  mapping (address => mapping (address => uint256)) public allowed;

  /**
   * @dev Constructor for CheckpointToken, initializing the token
   *
   * Here we define initial values for name, symbol and decimals.
   *
   * @param _name Initial name of the token
   * @param _symbol Initial symbol of the token
   * @param _decimals Number of decimals for the token, industry standard is 18
   */
  function CheckpointToken(string _name, string _symbol, uint256 _decimals) public {
    name = _name;
    symbol = _symbol;
    decimals = _decimals;
  }

  /** PUBLIC FUNCTIONS
   ****************************************/

  /**
   * @dev Function to check the amount of tokens that an owner allowed to a spender.
   * @param owner address The address which owns the funds.
   * @param spender address The address which will spend the funds.
   * @return A uint256 specifying the amount of tokens still available for the spender.
   */
  function allowance(address owner, address spender) public view returns (uint256) {
    return allowed[owner][spender];
  }

  /**
   * @dev Approve the passed address to spend the specified amount of tokens on behalf of msg.sender.
   *
   * Beware that changing an allowance with this method brings the risk that someone may use both the old
   * and the new allowance by unfortunate transaction ordering. One possible solution to mitigate this
   * race condition is to first reduce the spender's allowance to 0 and set the desired value afterwards:
   * https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
   * @param spender The address which will spend the funds.
   * @param value The amount of tokens to be spent.
   * @return true if the call function was executed successfully
   */
  function approve(address spender, uint256 value) public returns (bool) {
    allowed[msg.sender][spender] = value;
    Approval(msg.sender, spender, value);
    return true;
  }

  /**
   * @dev Transfer tokens from one address to another
   * @param from address The address which you want to send tokens from
   * @param to address The address which you want to transfer to
   * @param value uint256 the amount of tokens to be transferred
   * @return true if the call function was executed successfully
   */
  function transferFrom(address from, address to, uint256 value) public returns (bool) {
    require(value <= allowed[from][msg.sender]);

    value = verifyTransaction(from, to, value);

    transferInternal(from, to, value);
    Transfer(from, to, value);
    return true;
  }

  /**
   * @dev transfer token for a specified address
   * @param to The address to transfer to.
   * @param value The amount to be transferred.
   * @return true if the call function was executed successfully
   */
  function transfer(address to, uint256 value) public returns (bool) {
    value = verifyTransaction(msg.sender, to, value);

    transferInternal(msg.sender, to, value);
    Transfer(msg.sender, to, value);
    return true;
  }

  /**
   * @dev total number of tokens in existence
   * @return A uint256 specifying the total number of tokens in existence
   */
  function totalSupply() public view returns (uint256 tokenCount) {
    tokenCount = balanceAtCheckpoint(tokensTotal, currentCheckpointID);
  }

  /**
   * @dev total number of tokens in existence at the given checkpoint
   * @param checkpointID The checkpoint ID number we want to query for the total supply
   * @return A uint256 specifying the total number of tokens at a given checkpoint
   */
  function totalSupplyAt(uint256 checkpointID) public view returns (uint256 tokenCount) {
    tokenCount = balanceAtCheckpoint(tokensTotal, checkpointID);
  }

  /**
   * @dev Gets the balance of the specified address.
   * @param owner The address to query the the balance of.
   * @return An uint256 representing the amount owned by the passed address.
   */
  function balanceOf(address owner) public view returns (uint256 balance) {
    balance = balanceAtCheckpoint(tokenBalances[owner], currentCheckpointID);
  }

  /**
   * @dev Gets the balance of the specified address.
   * @param owner The address to query the the balance of.
   * @param checkpointID The checkpoint number we want to query for the balance.
   * @return An uint256 representing the amount owned by the passed address.
   */
  function balanceAt(address owner, uint256 checkpointID) public view returns (uint256 balance) {
    balance = balanceAtCheckpoint(tokenBalances[owner], checkpointID);
  }

  /**
   * @dev Increase the amount of tokens that an owner allowed to a spender.
   *
   * approve should be called when allowed[spender] == 0. To increment
   * allowed value is better to use this function to avoid 2 calls (and wait until
   * the first transaction is mined)
   * From MonolithDAO Token.sol
   * @param spender The address which will spend the funds.
   * @param addedValue The amount of tokens to increase the allowance by.
   */
  function increaseApproval(address spender, uint addedValue) public returns (bool) {
    allowed[msg.sender][spender] = allowed[msg.sender][spender].add(addedValue);
    Approval(msg.sender, spender, allowed[msg.sender][spender]);
    return true;
  }

  /**
   * @dev Decrease the amount of tokens that an owner allowed to a spender.
   *
   * approve should be called when allowed[spender] == 0. To decrement
   * allowed value is better to use this function to avoid 2 calls (and wait until
   * the first transaction is mined)
   * From MonolithDAO Token.sol
   * @param spender The address which will spend the funds.
   * @param subtractedValue The amount of tokens to decrease the allowance by.
   */
  function decreaseApproval(address spender, uint subtractedValue) public returns (bool) {
    uint oldValue = allowed[msg.sender][spender];
    if (subtractedValue > oldValue) {
      allowed[msg.sender][spender] = 0;
    } else {
      allowed[msg.sender][spender] = oldValue.sub(subtractedValue);
    }
    Approval(msg.sender, spender, allowed[msg.sender][spender]);
    return true;
  }

  /**
   * @dev Addition to StandardToken methods. Increase the amount of tokens that
   * an owner allowed to a spender and execute a call with the sent data.
   *
   * This is originally from OpenZeppelin.
   *
   * approve should be called when allowed[spender] == 0. To increment
   * allowed value is better to use this function to avoid 2 calls (and wait until
   * the first transaction is mined)
   * From MonolithDAO Token.sol
   * @param spender The address which will spend the funds.
   * @param addedValue The amount of tokens to increase the allowance by.
   * @param data ABI-encoded contract call to call `spender` address.
   */
  function increaseApproval(address spender, uint addedValue, bytes data) public returns (bool) {
    require(spender != address(this));

    increaseApproval(spender, addedValue);

    require(spender.call(data));

    return true;
  }

  /**
   * @dev Addition to StandardToken methods. Decrease the amount of tokens that
   * an owner allowed to a spender and execute a call with the sent data.
   *
   * This is originally from OpenZeppelin.
   *
   * approve should be called when allowed[spender] == 0. To decrement
   * allowed value is better to use this function to avoid 2 calls (and wait until
   * the first transaction is mined)
   * From MonolithDAO Token.sol
   * @param spender The address which will spend the funds.
   * @param subtractedValue The amount of tokens to decrease the allowance by.
   * @param data ABI-encoded contract call to call `spender` address.
   */
  function decreaseApproval(address spender, uint subtractedValue, bytes data) public returns (bool) {
    require(spender != address(this));

    decreaseApproval(spender, subtractedValue);

    require(spender.call(data));

    return true;
  }

  /** INTERNALS
   ****************************************/

  function balanceAtCheckpoint(Checkpoint[] storage checkpoints, uint256 checkpointID) internal returns (uint256 balance) {
    uint256 currentCheckpointID;
    (currentCheckpointID, balance) = getCheckpoint(checkpoints, checkpointID);
  }

  function verifyTransaction(address from, address to, uint256 value) internal returns (uint256) {
    if (address(transactionVerifier) != address(0)) {
      value = transactionVerifier.verify(from, to, value);
    }

    // Per EIP20 standard, value == 0 is a valid transaction, and should not throw
    return value;
  }

  function transferInternal(address from, address to, uint256 value) internal {
    uint256 fromBalance = balanceOf(from);
    uint256 toBalance = balanceOf(to);

    setCheckpoint(tokenBalances[from], fromBalance.sub(value));
    setCheckpoint(tokenBalances[to], toBalance.add(value));
  }

  function createCheckpoint() internal returns (uint256 checkpointID) {
    currentCheckpointID = currentCheckpointID + 1;
    return currentCheckpointID;
  }


  /** CORE
   ** The Magic happens below:
   ***************************************/

  function setCheckpoint(Checkpoint[] storage checkpoints, uint256 newValue) internal {
    if ((checkpoints.length == 0) || (checkpoints[checkpoints.length.sub(1)].checkpointID < currentCheckpointID)) {
      checkpoints.push(Checkpoint(currentCheckpointID, newValue));
    } else {
       checkpoints[checkpoints.length.sub(1)] = Checkpoint(currentCheckpointID, newValue);
    }
  }

  function getCheckpoint(Checkpoint[] storage checkpoints, uint256 checkpointID) internal returns (uint256 checkpointID_, uint256 value) {
    if (checkpoints.length == 0) {
      return (0, 0);
    }

    // Shortcut for the actual value
    if (checkpointID >= checkpoints[checkpoints.length.sub(1)].checkpointID) {
      return (checkpoints[checkpoints.length.sub(1)].checkpointID, checkpoints[checkpoints.length.sub(1)].value);
    }

    if (checkpointID < checkpoints[0].checkpointID) {
      return (0, 0);
    }

    // Binary search of the value in the array
    uint256 min = 0;
    uint256 max = checkpoints.length.sub(1);
    while (max > min) {
      uint256 mid = (max.add(min.add(1))).div(2);
      if (checkpoints[mid].checkpointID <= checkpointID) {
        min = mid;
      } else {
        max = mid.sub(1);
      }
    }

    return (checkpoints[min].checkpointID, checkpoints[min].value);
  }
}
