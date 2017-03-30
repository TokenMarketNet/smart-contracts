pragma solidity ^0.4.8;

import "zeppelin/contracts/ownership/Ownable.sol";
import "zeppelin/contracts/token/TransferableToken.sol";
import "zeppelin/contracts/token/ERC20.sol";


/**
 * Define interface for releasing the token transfer after a successful crowdsale.
 */
contract ReleasableToken is ERC20, Ownable {

  /* The crowdsale contrcat that allows unlift the transfer limits on this token */
  address public releaseAgent;

  /** A crowdsale contract can release us to the wild if ICO success. If false we are are in transfer lock up period.*/
  bool public released = false;

  /** List of agents that are allowed to transfer tokens regardless of the lock down period. These are crowdsale contracts and possible the owner itself. */
  mapping (address => bool) public transferAgents;

  /**
   * Limit token transfer until the crowdsale is over.
   *
   */
  modifier canTransfer(address _sender, uint _value) {

    if(!released) {
        if(!transferAgents[_sender]) {
            throw;
        }
    }

    // Perform with the normal balance check
    if (_value > transferableTokens(_sender, uint64(now))) throw;

    _;
  }

  /**
   * Set the contract that can call release.
   */
  function setReleaseAgent(address addr) onlyOwner inReleaseState(false) public {

    // Already set
    if(releaseAgent != 0) {
      throw;
    }

    // We don't do interface check here as we might want to a normal wallet address to act as a release agent
    releaseAgent = addr;
  }

  /**
   * Owner can allow a particular address (crowdsale contract) to transfer tokens despite the lock up period.
   */
  function setTransferAgent(address addr, bool state) onlyOwner inReleaseState(false) public {
    transferAgents[addr] = state;
  }

  /**
   * One way function to release the tokens to the wild.
   *
   * Can be called only from the release agent that is the final ICO contract. It is only called if the crowdsale has been success (first milestone reached).
   */
  function releaseTokenTransfer() public onlyReleaseAgent {
    // np: David Hasselhoff - Looking for freedom
    released = true;
  }

  /** The function can be called only before or after the tokens have been releasesd */
  modifier inReleaseState(bool releaseState) {
    if(releaseState != released) {
        throw;
    }
    _;
  }

  /** The function can be called only by a whitelisted release agent. */
  modifier onlyReleaseAgent() {
    if(msg.sender != releaseAgent) {
        throw;
    }
    _;
  }

  function transfer(address _to, uint _value) canTransfer(msg.sender, _value) returns (bool success) {
   return super.transfer(_to, _value);
  }

  function transferFrom(address _from, address _to, uint _value) canTransfer(_from, _value) returns (bool success) {
   return super.transferFrom(_from, _to, _value);
  }

  function transferableTokens(address holder, uint64 time) constant public returns (uint256) {
    return balanceOf(holder);
  }

}
