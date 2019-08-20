pragma solidity ^0.4.24;

/**
 * @title Shared contract for KYC User Attributes
 * @dev You can inherit this contract for convenient access to KYCAttribute
 */
contract KYCAttributes {
  /**
   * @dev Here we define all the built-in KYC Attributes.
   *      Keep in mind, that the deployed contract can handle more attributes
   *      than these (up to 256 in total).
   *
   *      Attributes:
   *      KYCCleared    User have successfully completed KYC
   *      CanPushTokens User can send tokens to any address ("push"), despite of recipients KYC status
   */
  enum KYCAttribute {KYCCleared, CanPushTokens}
}
