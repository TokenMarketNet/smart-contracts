import "./Crowdsale.sol";
import "./BytesDeserializer.sol";

/**
 * A crowdsale that allows only signed payload with server-side specified buy in limits.
 *
 */
contract AMLCrowdsale is Crowdsale {

  using BytesDeserializer for bytes;

  /** How much ETH each custoemr has invested to this crowdsale */
  mapping (uint128 => uint256) public investedCustomerAmountOf;

  // The bytes payload set on the server side
  // total 28 bytes
  struct AMLPayload {

    /** Customer whitelisted address where the deposit can come from */
    address whitelistedAddress; // 16 bytes

    /** Customer id, UUID v4 */
    uint128 customerId; // 8 bytes

    /** Min amount this customer needs to invest in ETH. Set zero if no minimum. */
    uint16 minETH; // 2 bytes

    /** Max amount this customer can to invest in ETH. Set zero if no maximum.  */
    uint16 maxETH; // 2 bytes
  }



  /**
   * Deconstruct server-side byte data to structured data.
   */
  function deserializeAMLPayload(bytes datagram) private returns(AMLPayload decodedPayload) {

  }


  /**
   * @param customerMin (optional, can be zero) How much this customer needs to invest.
   *                    A signed server side set parameter by the current AML policy.
   * @param customerMax (optional, can be zero) How much this customer can invest.
   *                    A signed server side set parameter by the current AML policy.
   */
  function checkAMLLimits(uint128 customerId, uint weiAmount, uint customerMin, uint customerMax) private {
    investedCustomerAmountOf[customerId] = investedCustomerAmountOf[customerId].plus(weiAmount);

    // Check AML boundaries (if given)
    if(customerMin != 0) {
      require(investedCustomerAmountOf[customerId] >= customerMin);
    }

    if(customerMax != 0) {
      require(investedCustomerAmountOf[customerId] <= customerMax);
    }
  }

  /**
   * AML purchase.
   *
   */
  function buyWithAMLData(bytes data, uint8 v, bytes32 r, bytes32 s) public payable {

    // We assume there is no serious min and max fluctuations for the customer, unless
    // especially set in the server side per customer manual override.
    // Otherwise the customer can reuse old data payload with different min or max value
    // to work around the per customer cap.

  }
}
