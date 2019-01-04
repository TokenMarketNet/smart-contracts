pragma solidity ^0.4.18;

import "./KYCInterface.sol";
import "zeppelin/contracts/ownership/Ownable.sol";

contract BasicKYC is Ownable, KYCInterface {
    mapping (address => uint128) whitelist;

    event Whitelisted(address who, uint128 nonce);

    function BasicKYC() Ownable() {
      // This is here for our verification code only
    }

    function setWhitelisting(address who, uint128 nonce) internal {
        whitelist[who] = nonce;

        Whitelisted(who, nonce);
    }

    function whitelistUser(address who, uint128 nonce) external onlyOwner {
        setWhitelisting(who, nonce);
    }

    function whitelistMe(uint128 nonce, uint8 v, bytes32 r, bytes32 s) external {
        bytes32 hash = keccak256(msg.sender, nonce);
        require(ecrecover(hash, v, r, s) == owner);
        require(whitelist[msg.sender] == 0);

        setWhitelisting(msg.sender, nonce);
    }

    function isWhitelisted(address who) external view returns(bool) {
        return whitelist[who] > 0;
    }
}
