import "./CrowdsaleBase.sol";
import "./AllocatedCrowdsaleMixin.sol";
import "./KYCPayloadDeserializer.sol";

/**
 * A crowdsale that allows only signed payload with server-side specified buy in limits.
 *
 *
 * The token distribution happens as in the allocated crowdsale.
 *
 */
contract KYCCrowdsale is AllocatedCrowdsaleMixin, KYCPayloadDeserializer {

  /* Server holds the private key to this address to decide if the AML payload is valid or not. */
  address public signerAddress;

  function KYCCrowdsale(address _token, PricingStrategy _pricingStrategy, address _multisigWallet, uint _start, uint _end, uint _minimumFundingGoal, address _beneficiary) CrowdsaleBase(_token, _pricingStrategy, _multisigWallet, _start, _end, _minimumFundingGoal) AllocatedCrowdsaleMixin(_beneficiary) {

  }

  /**
   * A token purchase with anti-money laundering
   *
   * ©return tokenAmount How many tokens where bought
   */
  function buyWithKYCData(bytes dataframe, uint8 v, bytes32 r, bytes32 s) public payable returns(uint tokenAmount) {

    // Check that the KYC data is signed by our server
    bytes32 hash = sha256(dataframe);
    require(ecrecover(hash, v, r, s) == signerAddress);

    KYCPayload memory payload = deserializeKYCPayload(dataframe);

    // Only whitelisted address can participate the transaction
    require(payload.whitelistedAddress == msg.sender);

    uint tokensBought = investInternal(msg.sender, payload.customerId);

    // We assume there is no serious min and max fluctuations for the customer, unless
    // especially set in the server side per customer manual override.
    // Otherwise the customer can reuse old data payload with different min or max value
    // to work around the per customer cap.
    require(investedAmountOf[payload.whitelistedAddress] >= payload.minETH * (10**18/1000));
    require(investedAmountOf[payload.whitelistedAddress] <= payload.maxETH * (10**18/1000));

    return tokensBought;
  }

}
