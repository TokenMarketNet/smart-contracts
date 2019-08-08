/**
 * This smart contract code is Copyright 2019 TokenMarket Ltd. For more information see https://tokenmarket.net
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 * NatSpec is used intentionally to cover also other than public functions
 * Solidity 0.4.18 is intentionally used: it's stable, and our framework is
 * based on that.
 */

pragma solidity ^0.4.25;

import "./KYCInterface.sol";
import "zeppelin/contracts/ownership/rbac/RBAC.sol";

/**
 * @author TokenMarket /  Ville Sundell <ville at tokenmarket.net>
 */
contract BasicKYC is RBAC, KYCInterface {
  /** @dev This mapping contains signature hashes which have been already used: */
  mapping (bytes32 => bool) public hashes;
  /** @dev Mapping of all the flags for all the users: */
  mapping (address => uint256) public flags;

  /** @dev These can be used from other contracts to avoid typos with roles: */
  string public constant ROLE_SIGNER = "signer";
  string public constant ROLE_SETTER = "setter";

  /**
   * @dev Interal function for setting the flags, and emmiting the event
   * @param user Address of the user whose flags we would like to set
   * @param newFlags Whole set of 256 flags
   */
  function writeFlags(address user, uint256 newFlags) internal {
    flags[user] = newFlags;

    emit FlagsSet(user, flags[user]);
  }

  /**
   * @dev Set all the flags for a user all in once
   * @param user Address of the user whose flags we would like to set
   * @param newFlags Whole set of 256 flags
   */
  function setFlags(address user, uint256 newFlags) external onlyRole(ROLE_SETTER) {
    writeFlags(user, newFlags);
  }

  /**
   * @dev Get a flag for a user, return true or false
   * @param user Address of the user whose flag we would like to have
   * @param flag Flag index from 0 to 255
   * @return Flag status, set or unset
   */
  function getFlag(address user, uint8 flag) external view returns (bool) {
    return (flags[user] & 2**flag) > 0;
  }

  /**
   * @dev Whitelist an address. User can whitelist themselves by using a
   *      signed message from server side.
   * @param signer Address of the server side signing key
   * @param newFlags 256 bit integer for all the flags for an address
   * @param nonce Value to prevent re-use of the server side signed data
   * @param v V of the server's key which was used to sign this transfer
   * @param r R of the server's key which was used to sign this transfer
   * @param s S of the server's key which was used to sign this transfer
   */
  function whitelistMe(address signer, uint256 newFlags, uint128 nonce, uint8 v, bytes32 r, bytes32 s) external {
    require(hasRole(signer, ROLE_SIGNER));

    bytes32 hash = keccak256(msg.sender, signer, newFlags, nonce);
    require(hashes[hash] == false);
    require(ecrecover(hash, v, r, s) == signer);

    hashes[hash] = true;
    writeFlags(msg.sender, newFlags);
  }

}
