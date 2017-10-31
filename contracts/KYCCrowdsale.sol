import "./Crowdsale.sol";
import "./KYCPayloadDeserializer.sol";

/**
 * A crowdsale that allows only signed payload with server-side specified buy in limits.
 *
 */
contract KYCCrowdsale is CrowdsaleBase, KYCPayloadDeserializer {

  /** How much ETH each custoemr has invested to this crowdsale */
  mapping (uint128 => uint256) public investedCustomerAmountOf;

  /* Server holds the private key to this address to decide if the AML payload is valid or not. */
  address public signerAddress;

  /**
   * A token purchase with anti-money laundering
   *
   */
  function buyWithKYCData(bytes data, uint8 v, bytes32 r, bytes32 s) public payable {

    bytes32 hash = sha256(data);
    require(ecrecover(hash, v, r, s) == signerAddress);

    // We assume there is no serious min and max fluctuations for the customer, unless
    // especially set in the server side per customer manual override.
    // Otherwise the customer can reuse old data payload with different min or max value
    // to work around the per customer cap.


    // investInternal(addr, customerId);

  }

}
