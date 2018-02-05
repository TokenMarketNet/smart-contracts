import "./CrowdsaleBase.sol";
import "./AllocatedCrowdsaleMixin.sol";
import "./KYCPayloadDeserializer.sol";

/**
 * A presale smart contract that collects money from SAFT/SAFTE agreed buyers.
 *
 * Presale contract where we collect money for the token that does not exist yet.
 * The same KYC rules apply as in KYCCrowdsale. No tokens are issued in this point,
 * but they are delivered to the buyers after the token sale is over.
 *
 */
contract KYCPresale is AllocatedCrowdsaleMixin, KYCPayloadDeserializer {

  /** Server holds the private key to this address to decide if the AML payload is valid or not. */
  address public signerAddress;

  /** A new server-side signer key was set to be effective */
  event SignerChanged(address signer);

  /** An user made a prepurchase through KYC'ed interface. The money has been moved to the token sale multisig wallet. The buyer will receive their tokens in an airdrop after the token sale is over. */
  event Prepurchased(address investor, uint weiAmount, uint tokenAmount, uint128 customerId, uint256 pricingInfo);

  /**
   * Constructor.
   */
  function KYCPresale(address _token, PricingStrategy _pricingStrategy, address _multisigWallet, uint _start, uint _end, uint _minimumFundingGoal, address _beneficiary) CrowdsaleBase(_token, _pricingStrategy, _multisigWallet, _start, _end, _minimumFundingGoal) AllocatedCrowdsaleMixin(_beneficiary) {

  }

  /**
   * A token purchase with anti-money laundering
   *
   * ©return tokenAmount How many tokens where bought
   */
  function buyWithKYCData(bytes dataframe, uint8 v, bytes32 r, bytes32 s) public payable returns(uint tokenAmount) {
    bytes32 hash = sha256(dataframe);
    var (whitelistedAddress, customerId, minETH, maxETH, pricingInfo) = getKYCPresalePayload(dataframe);
    uint multiplier = 10 ** 18;
    address receiver = msg.sender;
    uint weiAmount = msg.value;

    // The payload was created by token sale server
    require(ecrecover(hash, v, r, s) == signerAddress);

    // Determine if it's a good time to accept investment from this participant
    if(getState() == State.PreFunding) {
      // Are we whitelisted for early deposit
      require(earlyParticipantWhitelist[receiver]);
    } else if(getState() == State.Funding) {
      // Retail participants can only come in when the crowdsale is running
      // pass
    } else {
      // Unwanted state
      revert;
    }

    if(investedAmountOf[receiver] == 0) {
       // A new investor
       investorCount++;
    }

    // Update per investor amount
    investedAmountOf[receiver] = investedAmountOf[receiver].plus(weiAmount);

    // Update totals
    weiRaised = weiRaised.plus(weiAmount);

    // Check that we did not bust the cap
    require(!isBreakingCap(weiAmount, tokenAmount, weiRaised, tokensSold));

    require(investedAmountOf[msg.sender] >= minETH * multiplier / 10000);
    require(investedAmountOf[msg.sender] <= maxETH * multiplier / 10000);

    // Pocket the money, or fail the crowdsale if we for some reason cannot send the money to our multisig
    require(multisigWallet.send(weiAmount));

    // Tell us invest was success
    Prepurchased(receiver, weiAmount, tokenAmount, customerId, pricingInfo);

    return 0; // In presale we do not issue actual tokens tyet
  }

  /// @dev This function can set the server side address
  /// @param _signerAddress The address derived from server's private key
  function setSignerAddress(address _signerAddress) onlyOwner {
    signerAddress = _signerAddress;
    SignerChanged(signerAddress);
  }

}
