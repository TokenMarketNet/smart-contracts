pragma solidity ^0.4.8;

import "../ReleaseAgent.sol";
import "../ReleasableToken.sol";


/**
 * To test transfer lock up release.
 */
contract SimpleReleaseAgent is ReleaseAgent {

  ReleasableToken token;

  function SimpleReleaseAgent(ReleasableToken _token) {
    token = _token;
  }

  function isReleaseAgent() public returns(bool) {
    return true;
  }

  function release() {
    token.releaseTokenTransfer();
  }
}
