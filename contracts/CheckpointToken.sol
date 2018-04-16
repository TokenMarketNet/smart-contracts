pragma solidity ^0.4.18;

import "./CrowdsaleToken.sol";
import "zeppelin/contracts/math/SafeMath.sol";
import "zeppelin/contracts/ownership/Whitelist.sol";
import "zeppelin/contracts/token/ERC20/ERC20.sol";
import "zeppelin/contracts/token/ERC827/ERC827Token.sol";

contract CheckpointToken is ERC20, ERC827Token {
  using SafeMath for uint256;

  string public version = 'TAPAS 0.1';
  string public name;
  string public symbol;
  uint256 public decimals;

  struct Checkpoint {
    uint256 blockNumber; // We use uints for security reasons (no boxing)
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
    transferInternal(from, to, value);
    Transfer(from, to, value);
  }

  function transfer(address to, uint256 value) public returns (bool) {
    transferInternal(msg.sender, to, value);
    Transfer(msg.sender, to, value);
  }

  function totalSupply() public view returns (uint256 tokenCount) {
    uint256 blockNumber;
    (blockNumber, tokenCount) = getCheckpoint(tokensTotal, block.number);
  }

  function balanceOf(address who) public view returns (uint256 balance) {
    /// TODO: Should we return more than one parameter?
    balance = balanceAtBlock(who, block.number);
  }

  function balanceAt(address who, uint256 blockNumber) external view returns (uint256 balance) {
    balance = balanceAtBlock(who, blockNumber);
  }

  // INTERNALS
  function balanceAtBlock(address who, uint256 blockNumber) internal returns (uint256 balance) {
    uint256 currentBlockNumber;
    (currentBlockNumber, balance) = getCheckpoint(tokenBalances[who], blockNumber);
  }

  function transferInternal(address from, address to, uint256 value) internal {
    // TODO: Make a failsafe transport mechanism to transfer manually, maybe the dependant contract would need it, and not this one?
    uint256 fromBalance;
    uint256 toBalance;

    fromBalance = balanceOf(from);
    toBalance = balanceOf(to);

    setCheckpoint(tokenBalances[from], fromBalance.sub(value)); // TODO: FIX
    setCheckpoint(tokenBalances[to], toBalance.add(value));
  }

  function setCheckpoint(Checkpoint[] storage checkpoints, uint256 newValue) internal {
    if ((checkpoints.length == 0) || (checkpoints[checkpoints.length -1].blockNumber < block.number)) {
      checkpoints.push(Checkpoint(block.number, newValue));
    } else {
       checkpoints[checkpoints.length-1] = Checkpoint(block.number, newValue);
    }
  }

  function getCheckpoint(Checkpoint[] storage checkpoints, uint256 blockNumber) internal returns (uint256 blockNumber_, uint256 value) {
    if (checkpoints.length == 0) return (0, 0);

    // Shortcut for the actual value
    if (blockNumber >= checkpoints[checkpoints.length-1].blockNumber) {
      return (checkpoints[checkpoints.length-1].blockNumber, checkpoints[checkpoints.length-1].value);
    }

    if (blockNumber < checkpoints[0].blockNumber) {
      return (0, 0);
    }

    // Binary search of the value in the array
    uint256 min = 0;
    uint256 max = checkpoints.length-1;
    while (max > min) {
      uint256 mid = (max + min + 1)/ 2;
      if (checkpoints[mid].blockNumber <= blockNumber) {
        min = mid;
      } else {
        max = mid-1;
      }
    }

    return (checkpoints[min].blockNumber, checkpoints[min].value);
  }

}
