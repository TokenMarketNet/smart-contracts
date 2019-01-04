pragma solidity ^0.4.18;

interface KYCInterface {
    event Whitelisted(address who, uint128 nonce);

    function whitelistUser(address who, uint128 nonce) external;

    function whitelistMe(uint128 nonce, uint8 v, bytes32 r, bytes32 s) external;

    function isWhitelisted(address who) external view returns(bool);
}
