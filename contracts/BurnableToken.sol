/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.8;

import "./StandardTokenExt.sol";

contract BurnableToken is StandardTokenExt {

  // @notice An address for the transfer event where the burned tokens are transferred in a faux Transfer event
  address public constant BURN_ADDRESS = 0;

  /** How many tokens we burned */
  event Burned(address burner, uint burnedAmount);

  /**
   * Burn extra tokens from a balance.
   *
   */
  function burn(uint burnAmount) {
    address burner = msg.sender;
    balances[burner] = balances[burner].sub(burnAmount);
    totalSupply = totalSupply.sub(burnAmount);
    Burned(burner, burnAmount);

    // Inform the blockchain explores that track the
    // balances only by a transfer event that the balance in this
    // address has decreased
    Transfer(burner, BURN_ADDRESS, burnAmount);
  }
}
