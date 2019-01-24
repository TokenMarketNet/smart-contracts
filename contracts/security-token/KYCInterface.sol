pragma solidity ^0.4.18;

interface KYCInterface {
    event Whitelisted(address who, uint128 nonce);

    function isWhitelisted(address who) external view returns(bool);
}
