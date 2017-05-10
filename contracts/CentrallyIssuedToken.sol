pragma solidity ^0.4.6;

import "./BurnableToken.sol";
import "./UpgradeableToken.sol";


/**
 * Centrally issued Ethereum token.
 *
 * We mix in burnable and upgradeable traits.
 *
 * Token supply is created in the token contract creation and allocated to owner.
 * The owner can then transfer from its supply to crowdsale participants.
 * The owner, or anybody, can burn any excessive tokens they are holding.
 *
 */
contract CentrallyIssuedToken is BurnableToken, UpgradeableToken {

  string public name;
  string public symbol;
  uint public decimals;

  function CentrallyIssuedToken(address _owner, string _name, string _symbol, uint _totalSupply, uint _decimals)  UpgradeableToken(_owner) {
    name = _name;
    symbol = _symbol;
    totalSupply = _totalSupply;
    decimals = _decimals;

    // Allocate initial balance to the owner
    balances[_owner] = _totalSupply;
  }
}
