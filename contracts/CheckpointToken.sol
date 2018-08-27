/**
 * This smart contract code is Copyright 2018 TokenMarket Ltd. For more information see https://tokenmarket.net
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 * NatSpec is used intentionally to cover also other than public functions
 * Solidity 0.4.18 is intentionally used: it's stable, and our framework is
 * based on that.
 */

pragma solidity ^0.4.18;

import "./CrowdsaleToken.sol";
import "zeppelin/contracts/math/SafeMath.sol";
import "zeppelin/contracts/ownership/Whitelist.sol";
import "zeppelin/contracts/token/ERC20/ERC20.sol";
import "zeppelin/contracts/token/ERC827/ERC827Token.sol";

/**
 * @author TokenMarket /  Ville Sundell <ville at tokenmarket.net>
 */
contract CheckpointToken is ERC20, ERC827 {
  using SafeMath for uint256; // We use only uint256 for safety reasons (no boxing)

  string public name;
  string public symbol;
  uint256 public decimals;
  uint256 public freezedAt = 0;
  uint256 public freezeDuration = 1 days; // Default is one day

  struct Checkpoint {
    uint256 blockNumber;
    uint256 value;
  }

  mapping (address => Checkpoint[]) public tokenBalances;
  Checkpoint[] public tokensTotal;

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
    transferInternal(msg.sender, to, value);
    Transfer(msg.sender, to, value);
    return true;
  }

  /**
   * @dev total number of tokens in existence
   * @return A uint256 specifying the total number of tokens in existence
   */
  function totalSupply() public view returns (uint256 tokenCount) {
    tokenCount = balanceAtBlock(tokensTotal, block.number);
  }

  /**
   * @dev total number of tokens in existence at the given block
   * @param blockNumber The block number we want to query for the total supply
   * @return A uint256 specifying the total number of tokens at a given block
   */
  function totalSupplyAt(uint256 blockNumber) public view returns (uint256 tokenCount) {
    tokenCount = balanceAtBlock(tokensTotal, blockNumber);
  }

  /**
   * @dev Gets the balance of the specified address.
   * @param owner The address to query the the balance of.
   * @return An uint256 representing the amount owned by the passed address.
   */
  function balanceOf(address owner) public view returns (uint256 balance) {
    balance = balanceAtBlock(tokenBalances[owner], block.number);
  }

  /**
   * @dev Gets the balance of the specified address.
   * @param owner The address to query the the balance of.
   * @param blockNumber The block number we want to query for the balance.
   * @return An uint256 representing the amount owned by the passed address.
   */
  function balanceAt(address owner, uint256 blockNumber) public view returns (uint256 balance) {
    balance = balanceAtBlock(tokenBalances[owner], blockNumber);
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

  /** ERC827 Functions from OpenZeppelin
   ****************************************/

  /**
    * @dev Addition to ERC20 token methods. It allows to
    * approve the transfer of value and execute a call with the sent data.
    *
    * Beware that changing an allowance with this method brings the risk that
    * someone may use both the old and the new allowance by unfortunate
    * transaction ordering. One possible solution to mitigate this race condition
    * is to first reduce the spender's allowance to 0 and set the desired value
    * afterwards:
    * https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
    *
    * @param spender The address that will spend the funds.
    * @param value The amount of tokens to be spent.
    * @param data ABI-encoded contract call to call `_to` address.
    *
    * @return true if the call function was executed successfully
    */
  function approve(address spender, uint256 value, bytes data) public returns (bool) {
    require(spender != address(this));

    approve(spender, value);

    require(spender.call(data));

    return true;
  }

  /**
   * @dev Addition to ERC20 token methods. Transfer tokens to a specified
   * address and execute a call with the sent data on the same transaction
   *
   * @param to address The address which you want to transfer to
   * @param value uint256 the amout of tokens to be transfered
   * @param data ABI-encoded contract call to call `_to` address.
   *
   * @return true if the call function was executed successfully
   */
  function transfer(address to, uint256 value, bytes data) public returns (bool) {
    require(to != address(this));

    transfer(to, value);

    require(to.call(data));
    return true;
  }

  /**
   * @dev Addition to ERC20 token methods. Transfer tokens from one address to
   * another and make a contract call on the same transaction
   *
   * @param from The address which you want to send tokens from
   * @param to The address which you want to transfer to
   * @param value The amout of tokens to be transferred
   * @param data ABI-encoded contract call to call `_to` address.
   *
   * @return true if the call function was executed successfully
   */
  function transferFrom(address from, address to, uint256 value, bytes data) public returns (bool) {
    require(to != address(this));

    transferFrom(from, to, value);

    require(to.call(data));
    return true;
  }

  /**
   * @dev Addition to StandardToken methods. Increase the amount of tokens that
   * an owner allowed to a spender and execute a call with the sent data.
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

  function balanceAtBlock(Checkpoint[] storage checkpoints, uint256 blockNumber) internal returns (uint256 balance) {
    uint256 currentBlockNumber;
    (currentBlockNumber, balance) = getCheckpoint(checkpoints, blockNumber);
  }

  function transferInternal(address from, address to, uint256 value) internal {
    require(now > (freezedAt + freezeDuration));

    uint256 fromBalance;
    uint256 toBalance;

    fromBalance = balanceOf(from);
    toBalance = balanceOf(to);

    setCheckpoint(tokenBalances[from], fromBalance.sub(value));
    setCheckpoint(tokenBalances[to], toBalance.add(value));
  }


  /** CORE
   ** The Magic happens below:
   ***************************************/

  function setCheckpoint(Checkpoint[] storage checkpoints, uint256 newValue) internal {
    if ((checkpoints.length == 0) || (checkpoints[checkpoints.length.sub(1)].blockNumber < block.number)) {
      checkpoints.push(Checkpoint(block.number, newValue));
    } else {
       checkpoints[checkpoints.length.sub(1)] = Checkpoint(block.number, newValue);
    }
  }

  function getCheckpoint(Checkpoint[] storage checkpoints, uint256 blockNumber) internal returns (uint256 blockNumber_, uint256 value) {
    if (checkpoints.length == 0) {
      return (0, 0);
    }

    // Shortcut for the actual value
    if (blockNumber >= checkpoints[checkpoints.length.sub(1)].blockNumber) {
      return (checkpoints[checkpoints.length.sub(1)].blockNumber, checkpoints[checkpoints.length.sub(1)].value);
    }

    if (blockNumber < checkpoints[0].blockNumber) {
      return (0, 0);
    }

    // Binary search of the value in the array
    uint256 min = 0;
    uint256 max = checkpoints.length.sub(1);
    while (max > min) {
      uint256 mid = (max.add(min.add(1))).div(2);
      if (checkpoints[mid].blockNumber <= blockNumber) {
        min = mid;
      } else {
        max = mid.sub(1);
      }
    }

    return (checkpoints[min].blockNumber, checkpoints[min].value);
  }
}
