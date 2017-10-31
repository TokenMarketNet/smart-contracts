/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.14;

import "./BurnableCrowdsaleToken.sol";


/**
 * The AML Token
 *
 * This subset of BurnableCrowdsaleToken gives the Owner a possibility to
 * reclaim tokens from a participant before the token is released
 * after a participant has failed a prolonged AML process.
 */
contract AMLToken is BurnableCrowdsaleToken {

  // An event when the owner has reclaimed non-released tokens
  event OwnerReclaim(address fromWhom, uint amount);

  function AMLToken(string _name, string _symbol, uint _initialSupply, uint _decimals, bool _mintable) BurnableCrowdsaleToken(_name, _symbol, _initialSupply, _decimals, _mintable) {

  }

  /// @dev Here the owner can reclaim the tokens from a participant if
  ///      the token is not released yet
  /// @param fromWhom address of the participant whose tokens we want to claim
  function transferToOwner(address fromWhom) onlyOwner {
    if (released) revert();

    uint amount = balanceOf(fromWhom);
    balances[fromWhom] = balances[fromWhom].sub(amount);
    balances[owner] = balances[owner].add(amount);
    Transfer(fromWhom, owner, amount);
    OwnerReclaim(fromWhom, amount);
  }
}
