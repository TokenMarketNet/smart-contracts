/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */


import "./BytesDeserializer.sol";

/**
 * A mix-in contract to decode different AML payloads.
 *
 * @notice This should be a library, but for the complexity and toolchain fragility risks involving of linking library inside library, we put this as a mix-in.
 */
contract KYCPayloadDeserializer {

  using BytesDeserializer for bytes;

  // The bytes payload set on the server side
  // total 56 bytes

  struct KYCPayload {

    /** Customer whitelisted address where the deposit can come from */
    address whitelistedAddress; // 20 bytes

    /** Customer id, UUID v4 */
    uint128 customerId; // 16 bytes

    /**
     * Min amount this customer needs to invest in ETH. Set zero if no minimum. Expressed as parts of 10000. 1 ETH = 10000.
     * @notice Decided to use 32-bit words to make the copy-pasted Data field for the ICO transaction less lenghty.
     */
    uint32 minETH; // 4 bytes

    /** Max amount this customer can to invest in ETH. Set zero if no maximum. Expressed as parts of 10000. 1 ETH = 10000. */
    uint32 maxETH; // 4 bytes
  }

  /**
   * Deconstruct server-side byte data to structured data.
   */

  function deserializeKYCPayload(bytes dataframe) internal constant returns(KYCPayload decodedPayload) {
    KYCPayload payload;
    payload.whitelistedAddress = dataframe.sliceAddress(0);
    payload.customerId = uint128(dataframe.slice16(20));
    payload.minETH = uint32(dataframe.slice4(36));
    payload.maxETH = uint32(dataframe.slice4(40));
    return payload;
  }

  /**
   * Helper function to allow us to return the decoded payload to an external caller for testing.
   *
   * TODO: Some sort of compiler issue (?) with memory keyword. Tested with solc 0.4.16 and solc 0.4.18.
   * If used, makes KYCCrowdsale to set itself to a bad state getState() returns 5 (Failure). Overrides some memory?
   */
  /*
  function broken_getKYCPayload(bytes dataframe) public constant returns(address whitelistedAddress, uint128 customerId, uint32 minEth, uint32 maxEth) {
    KYCPayload memory payload = deserializeKYCPayload(dataframe);
    payload.whitelistedAddress = dataframe.sliceAddress(0);
    payload.customerId = uint128(dataframe.slice16(20));
    payload.minETH = uint32(dataframe.slice4(36));
    payload.maxETH = uint32(dataframe.slice4(40));
    return (payload.whitelistedAddress, payload.customerId, payload.minETH, payload.maxETH);
  }*/

  /**
   * Same as above, does not seem to cause any issue.
   */
  function getKYCPayload(bytes dataframe) public constant returns(address whitelistedAddress, uint128 customerId, uint32 minEth, uint32 maxEth) {
    address _whitelistedAddress = dataframe.sliceAddress(0);
    uint128 _customerId = uint128(dataframe.slice16(20));
    uint32 _minETH = uint32(dataframe.slice4(36));
    uint32 _maxETH = uint32(dataframe.slice4(40));
    return (_whitelistedAddress, _customerId, _minETH, _maxETH);
  }

}
