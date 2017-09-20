pragma solidity ^0.4.13;

import "zeppelin/contracts/ownership/Ownable.sol";
import "zeppelin/contracts/token/ERC20Basic.sol";

contract Recoverable is Ownable {

  /// @dev Empty constructor (for now)
  function Recoverable() {
  }

  /// @dev This will be invoked by the owner, when owner wants to rescue tokens
  /// @param token Token which will we rescue to the owner from the contract
  function recoverTokens(ERC20Basic token) onlyOwner public {
    token.transfer(owner, tokensToBeReturned(token));
  }

  /// @dev Interface function, can be overwritten by the superclass
  /// @param token Token which balance we will check and return
  /// @return The amount of tokens (in smallest denominator) the contract owns
  function tokensToBeReturned(ERC20Basic token) public returns (uint) {
    return token.balanceOf(this);
  }
}
