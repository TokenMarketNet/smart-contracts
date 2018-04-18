/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 * Author: Ville Sundell <ville at tokenmarket.net>
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.18;

import "./CrowdsaleToken.sol";
import "zeppelin/contracts/math/SafeMath.sol";
import "zeppelin/contracts/ownership/Whitelist.sol";
import "zeppelin/contracts/token/ERC20/ERC20.sol";
import "zeppelin/contracts/token/ERC827/ERC827Token.sol";

contract CheckpointToken is ERC20, ERC827 {
  using SafeMath for uint256; // We use only uint256 for safety reasons (no boxing)

  string public version = 'TAPAS 0.1';
  string public name;
  string public symbol;
  uint256 public decimals;

  struct Checkpoint {
    uint256 blockNumber;
    uint256 value;
  }

  mapping (address => Checkpoint[]) public tokenBalances;
  Checkpoint[] public tokensTotal;

  mapping (address => mapping (address => uint256)) public allowed;

  function CheckpointToken(string _name, string _symbol, uint256 _decimals) {
    name = _name;
    symbol = _symbol;
    decimals = _decimals;
  }

  // PUBLIC
  //////////

  function allowance(address owner, address spender) public view returns (uint256) {
    /// TODO: Should we use standardized argument names?
    return allowed[owner][spender];
  }

  function approve(address spender, uint256 value) public returns (bool) {
    allowed[msg.sender][spender] = value;
    Approval(msg.sender, spender, value);
    return true;
  }

  function transferFrom(address from, address to, uint256 value) public returns (bool) {
    require(value <= allowed[from][msg.sender]);

    transferInternal(from, to, value);
    Transfer(from, to, value);
  }

  function transfer(address to, uint256 value) public returns (bool) {
    transferInternal(msg.sender, to, value);
    Transfer(msg.sender, to, value);
  }

  function totalSupply() public view returns (uint256 tokenCount) {
    tokenCount = balanceAtBlock(tokensTotal, block.number);
  }

  function balanceOf(address who) public view returns (uint256 balance) {
    balance = balanceAtBlock(tokenBalances[who], block.number);
  }

  function balanceAt(address who, uint256 blockNumber) external view returns (uint256 balance) {
    balance = balanceAtBlock(tokenBalances[who], blockNumber);
  }

  /**
   * @dev Increase the amount of tokens that an owner allowed to a spender.
   *
   * approve should be called when allowed[_spender] == 0. To increment
   * allowed value is better to use this function to avoid 2 calls (and wait until
   * the first transaction is mined)
   * From MonolithDAO Token.sol
   * @param _spender The address which will spend the funds.
   * @param _addedValue The amount of tokens to increase the allowance by.
   */
  function increaseApproval(address _spender, uint _addedValue) public returns (bool) {
    allowed[msg.sender][_spender] = allowed[msg.sender][_spender].add(_addedValue);
    Approval(msg.sender, _spender, allowed[msg.sender][_spender]);
    return true;
  }

  /**
   * @dev Decrease the amount of tokens that an owner allowed to a spender.
   *
   * approve should be called when allowed[_spender] == 0. To decrement
   * allowed value is better to use this function to avoid 2 calls (and wait until
   * the first transaction is mined)
   * From MonolithDAO Token.sol
   * @param _spender The address which will spend the funds.
   * @param _subtractedValue The amount of tokens to decrease the allowance by.
   */
  function decreaseApproval(address _spender, uint _subtractedValue) public returns (bool) {
    uint oldValue = allowed[msg.sender][_spender];
    if (_subtractedValue > oldValue) {
      allowed[msg.sender][_spender] = 0;
    } else {
      allowed[msg.sender][_spender] = oldValue.sub(_subtractedValue);
    }
    Approval(msg.sender, _spender, allowed[msg.sender][_spender]);
    return true;
  }

  // ERC827 Functions from OpenZeppelin
  ////////////////////////
  /**
     @dev Addition to ERC20 token methods. It allows to
     approve the transfer of value and execute a call with the sent data.

     Beware that changing an allowance with this method brings the risk that
     someone may use both the old and the new allowance by unfortunate
     transaction ordering. One possible solution to mitigate this race condition
     is to first reduce the spender's allowance to 0 and set the desired value
     afterwards:
     https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729

     @param _spender The address that will spend the funds.
     @param _value The amount of tokens to be spent.
     @param _data ABI-encoded contract call to call `_to` address.

     @return true if the call function was executed successfully
   */
  function approve(address _spender, uint256 _value, bytes _data) public returns (bool) {
    require(_spender != address(this));

    approve(_spender, _value);

    require(_spender.call(_data));

    return true;
  }

  /**
     @dev Addition to ERC20 token methods. Transfer tokens to a specified
     address and execute a call with the sent data on the same transaction

     @param _to address The address which you want to transfer to
     @param _value uint256 the amout of tokens to be transfered
     @param _data ABI-encoded contract call to call `_to` address.

     @return true if the call function was executed successfully
   */
  function transfer(address _to, uint256 _value, bytes _data) public returns (bool) {
    require(_to != address(this));

    transfer(_to, _value);

    require(_to.call(_data));
    return true;
  }

  /**
     @dev Addition to ERC20 token methods. Transfer tokens from one address to
     another and make a contract call on the same transaction

     @param _from The address which you want to send tokens from
     @param _to The address which you want to transfer to
     @param _value The amout of tokens to be transferred
     @param _data ABI-encoded contract call to call `_to` address.

     @return true if the call function was executed successfully
   */
  function transferFrom(address _from, address _to, uint256 _value, bytes _data) public returns (bool) {
    require(_to != address(this));

    transferFrom(_from, _to, _value);

    require(_to.call(_data));
    return true;
  }

  /**
   * @dev Addition to StandardToken methods. Increase the amount of tokens that
   * an owner allowed to a spender and execute a call with the sent data.
   *
   * approve should be called when allowed[_spender] == 0. To increment
   * allowed value is better to use this function to avoid 2 calls (and wait until
   * the first transaction is mined)
   * From MonolithDAO Token.sol
   * @param _spender The address which will spend the funds.
   * @param _addedValue The amount of tokens to increase the allowance by.
   * @param _data ABI-encoded contract call to call `_spender` address.
   */
  function increaseApproval(address _spender, uint _addedValue, bytes _data) public returns (bool) {
    require(_spender != address(this));

    increaseApproval(_spender, _addedValue);

    require(_spender.call(_data));

    return true;
  }

  /**
   * @dev Addition to StandardToken methods. Decrease the amount of tokens that
   * an owner allowed to a spender and execute a call with the sent data.
   *
   * approve should be called when allowed[_spender] == 0. To decrement
   * allowed value is better to use this function to avoid 2 calls (and wait until
   * the first transaction is mined)
   * From MonolithDAO Token.sol
   * @param _spender The address which will spend the funds.
   * @param _subtractedValue The amount of tokens to decrease the allowance by.
   * @param _data ABI-encoded contract call to call `_spender` address.
   */
  function decreaseApproval(address _spender, uint _subtractedValue, bytes _data) public returns (bool) {
    require(_spender != address(this));

    decreaseApproval(_spender, _subtractedValue);

    require(_spender.call(_data));

    return true;
  }

  // INTERNALS
  /////////////

  function balanceAtBlock(Checkpoint[] storage checkpoints, uint256 blockNumber) internal returns (uint256 balance) {
    uint256 currentBlockNumber;
    (currentBlockNumber, balance) = getCheckpoint(checkpoints, blockNumber);
  }

  function transferInternal(address from, address to, uint256 value) internal {
    // TODO: Make a failsafe transport mechanism to transfer manually, maybe the dependant contract would need it, and not this one?
    uint256 fromBalance;
    uint256 toBalance;

    fromBalance = balanceOf(from);
    toBalance = balanceOf(to);

    setCheckpoint(tokenBalances[from], fromBalance.sub(value));
    setCheckpoint(tokenBalances[to], toBalance.add(value));
  }


  // CORE
  //////////////////////
  // The magic happens below:
  //////////////////////

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
