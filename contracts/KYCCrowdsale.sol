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

  /* A new server-side signer key was set to be effective */
  event SignerChanged(address signer);

  /**
   * Constructor.
   */
  function KYCCrowdsale(address _token, PricingStrategy _pricingStrategy, address _multisigWallet, uint _start, uint _end, uint _minimumFundingGoal, address _beneficiary) CrowdsaleBase(_token, _pricingStrategy, _multisigWallet, _start, _end, _minimumFundingGoal) AllocatedCrowdsaleMixin(_beneficiary) {

  }

  /**
   * A token purchase with anti-money laundering
   *
   * ©return tokenAmount How many tokens where bought
   */
  function buyWithKYCData(bytes dataframe, uint8 v, bytes32 r, bytes32 s) public payable returns(uint tokenAmount) {

    uint _tokenAmount;
    uint multiplier = 10 ** 18;

    // Perform signature check for normal addresses
    // (not deployment accounts, etc.)
    if(earlyParticipantWhitelist[msg.sender]) {
      // For test purchases use this faux customer id
      _tokenAmount = investInternal(msg.sender, 0x1000);

    } else {

      bytes32 hash = sha256(dataframe);

      var (whitelistedAddress, customerId, minETH, maxETH) = getKYCPayload(dataframe);

      // Check that the KYC data is signed by our server
      require(ecrecover(hash, v, r, s) == signerAddress);

      // Only whitelisted address can participate the transaction
      require(whitelistedAddress == msg.sender);

      _tokenAmount = investInternal(msg.sender, customerId);

    }

    if(!earlyParticipantWhitelist[msg.sender]) {
      // We assume there is no serious min and max fluctuations for the customer, unless
      // especially set in the server side per customer manual override.
      // Otherwise the customer can reuse old data payload with different min or max value
      // to work around the per customer cap.
      require(investedAmountOf[msg.sender] >= minETH * multiplier / 10000);
      require(investedAmountOf[msg.sender] <= maxETH * multiplier / 10000);
    }

    return _tokenAmount;
  }

  /// @dev This function can set the server side address
  /// @param _signerAddress The address derived from server's private key
  function setSignerAddress(address _signerAddress) onlyOwner {
    signerAddress = _signerAddress;
    SignerChanged(signerAddress);
  }

}
