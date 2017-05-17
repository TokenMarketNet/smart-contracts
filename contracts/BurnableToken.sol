pragma solidity ^0.4.8;

import './StandardToken.sol';


contract BurnableToken is StandardToken {

  address public constant BURN_ADDRESS = 0;

  /** How many tokens we burned */
  event Burned(address burner, uint burnedAmount);

  /**
   * Burn extra tokens from a balance.
   *
   */
  function burn(uint burnAmount) {
    address burner = msg.sender;
    balances[burner] = safeSub(balances[burner], burnAmount);
    totalSupply = safeSub(totalSupply, burnAmount);
    Burned(burner, burnAmount);

    // Keep exchanges happy by sending the burned amount to
    // "burn address"
    Transfer(burner, BURN_ADDRESS, burnAmount);
  }
}
