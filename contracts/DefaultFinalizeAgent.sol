/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.6;

import "./Crowdsale.sol";
import "./ReleasableToken.sol";

/**
 * The default behavior for the crowdsale end.
 *
 * Unlock tokens.
 */
contract DefaultFinalizeAgent is FinalizeAgent {

  ReleasableToken public token;
  Crowdsale public crowdsale;

  function DefaultFinalizeAgent(ReleasableToken _token, Crowdsale _crowdsale) {
    token = _token;
    crowdsale = _crowdsale;
  }

  /** Check that we can release the token */
  function isSane() public constant returns (bool) {
    return (token.releaseAgent() == address(this));
  }

  /** Called once by crowdsale finalize() if the sale was success. */
  function finalizeCrowdsale() public {
    if(msg.sender != address(crowdsale)) {
      throw;
    }
    token.releaseTokenTransfer();
  }

}
