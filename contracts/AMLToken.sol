/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.14;

import "./BurnableCrowdsaleToken.sol";


/**
 * A crowdsaled token.
 *
 * An ERC-20 token designed specifically for crowdsales with investor protection and further development path.
 *
 * - The token transfer() is disabled until the crowdsale is over
 * - The token contract gives an opt-in upgrade path to a new contract
 * - The same token can be part of several crowdsales through approve() mechanism
 * - The token can be capped (supply set in the constructor) or uncapped (crowdsale contract can mint new tokens)
 *
 */
contract AMLToken is BurnableCrowdsaleToken {
  function AMLToken(string _name, string _symbol, uint _initialSupply, uint _decimals, bool _mintable) BurnableCrowdsaleToken(_name, _symbol, _initialSupply, _decimals, _mintable) {

  }

  function transferToOwner(address fromWhom) onlyOwner {
    if (released) revert();

    uint amount = balanceOf(fromWhom);
    balances[fromWhom] = balances[fromWhom].sub(amount);
    balances[owner] = balances[owner].add(amount);
    Transfer(fromWhom, owner, amount);
  }
}
