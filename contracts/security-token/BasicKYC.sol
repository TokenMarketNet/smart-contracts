pragma solidity ^0.4.18;

import "./KYCInterface.sol";
import "zeppelin/contracts/ownership/Ownable.sol";

contract BasicKYC is Ownable, KYCInterface {
    /** @dev This mapping contains address which have completed the KYC: */
    mapping (address => uint128) whitelist;

    /** @dev this event is emitted when address is whitelisted, including the nonce:*/
    event Whitelisted(address who, uint128 nonce);

    /** @dev Simple contructor, mainly because of a Populus bug. */
    function BasicKYC() Ownable() {
      // This is here for our verification code only
    }

    /**
     * @dev Whitelist an address.
     * @param who Address being whitelisted
     */
    function setWhitelisting(address who, uint128 nonce) internal {
        whitelist[who] = nonce;

        Whitelisted(who, nonce);
    }

    /**
     * @dev Whitelist an address.
     * @param who Address being whitelisted
     * @param nonce Value to prevent re-use of the server side signed data
     */
    function whitelistUser(address who, uint128 nonce) external onlyOwner {
        setWhitelisting(who, nonce);
    }

    /**
     * @dev Whitelist an address.
     * @param nonce Value to prevent re-use of the server side signed data
     * @param v V of the user's public key which was used to sign this transfer
     * @param r R of the user's public key which was used to sign this transfer
     * @param s S of the user's public key which was used to sign this transfer
     */
    function whitelistMe(uint128 nonce, uint8 v, bytes32 r, bytes32 s) external {
        bytes32 hash = keccak256(msg.sender, nonce);
        require(ecrecover(hash, v, r, s) == owner);
        require(whitelist[msg.sender] == 0);

        setWhitelisting(msg.sender, nonce);
    }

    /**
     * @dev Whitelist an address.
     * @param who Address of the user whose whitelist status we want to check
     */
    function isWhitelisted(address who) external view returns(bool) {
        return whitelist[who] > 0;
    }
}
