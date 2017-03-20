pragma solidity ^0.4.6;

import "./Crowdsale.sol";
import "./ReleasableToken.sol";

/**
 * The default behavior for the crowdsale end.
 *
 * Unlock tokens.
 */
contract DefaultCrowdsaleFinal is FinalizeAgent, ReleaseAgent {

  ReleasableToken public token;
  Crowdsale public crowdsale;

  function DefaultCrowdsaleFinal(ReleasableToken _token, Crowdsale _crowdsale) {
    token = _token;
    crowdsale = _crowdsale;
  }

  /** Called once by crowdsale finalize() if the sale was success. */
  function finalizeCrowdsale() {
    if(msg.sender != address(crowdsale)) {
      throw;
    }
    token.releaseTokenTransfer();
  }

}