import "./Crowdsale.sol";

/**
 * A crowdsale that allows only signed payload with server-side specified buy in limits.
 *
 */
contract AMLCrowdsale is Crowdsale {

  /** How much ETH each custoemr has invested to this crowdsale */
  mapping (uint128 => uint256) public investedCustomerAmountOf;


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
