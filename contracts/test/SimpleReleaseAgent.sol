pragma solidity ^0.4.8;

import "../ReleasableToken.sol";


/**
 * To test transfer lock up release.
 */
contract SimpleReleaseAgent {

  ReleasableToken token;

  function SimpleReleaseAgent(ReleasableToken _token) {
    token = _token;
  }

  function release() {
    token.releaseTokenTransfer();
  }
}
