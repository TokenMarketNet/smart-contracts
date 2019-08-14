/**
 * This smart contract code is Copyright 2019 TokenMarket Ltd. For more information see https://tokenmarket.net
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 * NatSpec is used intentionally to cover also other than public functions
 * Solidity 0.4.18 is intentionally used: it's stable, and our framework is
 * based on that.
 */

pragma solidity ^0.4.24;

import "./KYCAttributes.sol";
import "./KYCInterface.sol";
import "zeppelin/contracts/ownership/rbac/RBAC.sol";

/**
 * @author TokenMarket /  Ville Sundell <ville at tokenmarket.net>
 */
contract BasicKYC is RBAC, KYCInterface, KYCAttributes {
  /** @dev This mapping contains signature hashes which have been already used: */
  mapping (bytes32 => bool) public hashes;
  /** @dev Mapping of all the attributes for all the users: */
  mapping (address => uint256) public attributes;

  /** @dev These can be used from other contracts to avoid typos with roles: */
  string public constant ROLE_SIGNER = "signer";
  string public constant ROLE_SETTER = "setter";

  /**
   * @dev Interal function for setting the attributes, and emmiting the event
   * @param user Address of the user whose attributes we would like to set
   * @param newAttributes Whole set of 256 attributes
   */
  function writeAttributes(address user, uint256 newAttributes) internal {
    attributes[user] = newAttributes;

    emit AttributesSet(user, attributes[user]);
  }

  /**
   * @dev Set all the attributes for a user all in once
   * @param user Address of the user whose attributes we would like to set
   * @param newAttributes Whole set of 256 attributes
   */
  function setAttributes(address user, uint256 newAttributes) external onlyRole(ROLE_SETTER) {
    writeAttributes(user, newAttributes);
  }

  /**
   * @dev Get a attribute for a user, return true or false
   * @param user Address of the user whose attribute we would like to have
   * @param attribute Attribute index from 0 to 255
   * @return Attribute status, set or unset
   */
  function getAttribute(address user, KYCAttribute attribute) external view returns (bool) {
    return (attributes[user] & 2**uint8(attribute)) > 0;
  }

  /**
   * @dev Set attributes an address. User can set their own attributes by using a
   *      signed message from server side.
   * @param signer Address of the server side signing key
   * @param newAttributes 256 bit integer for all the attributes for an address
   * @param nonce Value to prevent re-use of the server side signed data
   * @param v V of the server's key which was used to sign this transfer
   * @param r R of the server's key which was used to sign this transfer
   * @param s S of the server's key which was used to sign this transfer
   */
  function setMyAttributes(address signer, uint256 newAttributes, uint128 nonce, uint8 v, bytes32 r, bytes32 s) external {
    require(hasRole(signer, ROLE_SIGNER));

    bytes32 hash = keccak256(msg.sender, signer, newAttributes, nonce);
    require(hashes[hash] == false);
    require(ecrecover(hash, v, r, s) == signer);

    hashes[hash] = true;
    writeAttributes(msg.sender, newAttributes);
  }

}
