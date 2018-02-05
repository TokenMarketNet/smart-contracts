/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */


import "./BytesDeserializer.sol";

/**
 * A mix-in contract to decode different signed KYC payloads.
 *
 * @notice This should be a library, but for the complexity and toolchain fragility risks involving of linking library inside library, we currently use this as a helper method mix-in.
 */
contract KYCPayloadDeserializer {

  using BytesDeserializer for bytes;

  // @notice this struct describes what kind of data we include in the payload, we do not use this directly
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

    /**
     * Information about the price promised for this participant. It can be pricing tier id or directly one token price in weis.
     * @notice This is a later addition and not supported in all scenarios yet.
     */
    uint256 pricingInfo;
  }

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

  /**
   * Same as above, but with pricing information included in the payload as the last integer.
   *
   * @notice In a long run, deprecate the legacy methods above and only use this payload.
   */
  function getKYCPresalePayload(bytes dataframe) public constant returns(address whitelistedAddress, uint128 customerId, uint32 minEth, uint32 maxEth, uint256 pricingInfo) {
    address _whitelistedAddress = dataframe.sliceAddress(0);
    uint128 _customerId = uint128(dataframe.slice16(20));
    uint32 _minETH = uint32(dataframe.slice4(36));
    uint32 _maxETH = uint32(dataframe.slice4(40));
    uint256 _pricingInfo = uint256(dataframe.slice32(44));
    return (_whitelistedAddress, _customerId, _minETH, _maxETH, _pricingInfo);
  }

}
