import "zeppelin/contracts/token/ERC20.sol";
import "zeppelin/contracts/ownership/Ownable.sol";
import "zeppelin/contracts/token/StandardToken.sol";
import "./SafeMathLib.sol";


pragma solidity ^0.4.6;

/**
 * Token that has capabilities to increase its supply by another contract.
 *
 * This allows uncapped crowdsale by dynamically increasing the supply when money pours in.
 *
 */
contract MintableToken is StandardToken, Ownable {

  using SafeMathLib for uint;

  bool public mintingFinished = false;

  /** List of agents that are allowed to create new tokens */
  mapping (address => bool) public mintAgents;

  /**
   * Create new tokens and allocate them to an address..
   *
   * Only callably by a crowdsale contract (mint agent).
   */
  function mint(address receiver, uint amount) onlyMintAgent canMint public {
    totalSupply = totalSupply.plus(amount);
    balances[receiver] = balances[receiver].plus(amount);
    Transfer(0, receiver, amount);
  }

  /**
   * Owner can allow a crowdsale contract to mint new tokens.
   */
  function setMintAgent(address addr, bool state) onlyOwner canMint public {
    mintAgents[addr] = state;
  }

  modifier onlyMintAgent() {
    // Only crowdsale contracts are allowed to mint new tokens
    if(!mintAgents[msg.sender]) {
        throw;
    }
    _;
  }

  /** Make sure we are not done yet. */
  modifier canMint() {
    if(mintingFinished) throw;
    _;
  }
}
