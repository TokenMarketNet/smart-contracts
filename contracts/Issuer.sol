 pragma solidity ^0.4.8;

import 'zeppelin/contracts/token/StandardToken.sol';
import "zeppelin/contracts/ownership/Ownable.sol";

/**
 * Issuer manages token distribution after the crowdsale.
 *
 * This contract is fed a CSV file with Ethereum addresses and their
 * issued token balances.
 *
 * Issuer act as a gate keeper to ensure there is no double issuance
 * per address, in the case we need to do several issuance batches,
 * there is a race condition or there is a fat finger error.
 *
 * Issuer contract gets allowance from the team multisig to distribute tokens.
 *
 */
contract Issuer is Ownable {

  /** Map addresses whose tokens we have already issued. */
  mapping(address => bool) public issued;

  /** Centrally issued token we are distributing to our contributors */
  StandardToken public token;

  /** Party (team multisig) who is in the control of the token pool. Note that this will be different from the owner address (scripted) that calls this contract. */
  address public allower;

  /** How many addresses have received their tokens. */
  uint public issuedCount;

  function Issuer(address _owner, address _allower, StandardToken _token) {
    owner = _owner;
    allower = _allower;
    token = _token;
  }

  function issue(address benefactor, uint amount) onlyOwner {
    if(issued[benefactor]) throw;
    token.transferFrom(allower, benefactor, amount);
    issued[benefactor] = true;
    issuedCount += amount;
  }

}
