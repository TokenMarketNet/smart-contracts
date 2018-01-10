/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.8;

import "./StandardTokenExt.sol";
import "zeppelin/contracts/ownership/Ownable.sol";

/**
 * Issuer manages token distribution after the crowdsale.
 *
 * This contract is fed a CSV file with Ethereum addresses and their
 * issued token balances.
 *
 * Issuer act as a gate keeper to ensure there is no double issuance
 * per ID number, in the case we need to do several issuance batches,
 * there is a race condition or there is a fat finger error.
 *
 * Issuer contract gets allowance from the team multisig to distribute tokens.
 *
 */
contract IssuerWithId is Ownable {

  /** Map IDs whose tokens we have already issued. */
  mapping(uint => bool) public issued;

  /** Centrally issued token we are distributing to our contributors */
  StandardTokenExt public token;

  /** Party (team multisig) who is in the control of the token pool. Note that this will be different from the owner address (scripted) that calls this contract. */
  address public allower;

  /** How many tokens have been issued. */
  uint public issuedCount;

  /** Issue event **/
  event Issued(address benefactor, uint amount, uint id);

  function IssuerWithId(address _owner, address _allower, StandardTokenExt _token) {
    require(address(_owner) != address(0));
    require(address(_allower) != address(0));
    require(address(_token) != address(0));

    owner = _owner;
    allower = _allower;
    token = _token;
  }

  function issue(address benefactor, uint amount, uint id) onlyOwner {
    if(issued[id]) throw;
    token.transferFrom(allower, benefactor, amount);
    issued[id] = true;
    issuedCount += amount;

    Issued(benefactor, amount, id);
  }

}
