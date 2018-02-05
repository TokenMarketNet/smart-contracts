"""Signed address investing, containing pricing information for presale purposes."""

import uuid

import pytest
from eth_utils import to_checksum_address
from ethereum.tester import TransactionFailed
from eth_utils import to_wei
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.state import CrowdsaleState
from ico.sign import get_ethereum_address_from_private_key
from ico.sign import sign
from ico.kyc import pack_kyc_pricing_dataframe


@pytest.fixture
def private_key():
    """Server side private key."""
    return "Lehma take over Cancuu tacos"


@pytest.fixture
def initial_supply():
    return 1000000 * 10**18


@pytest.fixture
def signer_address(private_key):
    """Server side signer address."""
    return get_ethereum_address_from_private_key(private_key)


@pytest.fixture()
def kyc_finalize_agent(chain, uncapped_token, uncapped_flatprice) -> Contract:

    # Create finalizer contract
    args = [
        uncapped_token.address,
        uncapped_flatprice.address,
    ]
    contract, hash = chain.provider.deploy_contract('DefaultFinalizeAgent', deploy_args=args)
    return contract


@pytest.fixture
def kyc_presale(chain, team_multisig, preico_starts_at, preico_ends_at, preico_cap, preico_funding_goal, preico_token_allocation, signer_address, default_finalize_agent, initial_supply) -> Contract:
    """Create a Pre-ICO crowdsale contract."""

    # We provide a bogus token and pricing strategy for compatilibity reasons
    args = [
        team_multisig,
        preico_starts_at,
        preico_ends_at,
        99999 * 10**18
    ]

    tx = {
        "from": team_multisig,
    }

    contract, hash = chain.provider.deploy_contract('KYCPresale', deploy_args=args, deploy_transaction=tx)

    contract.transact({"from": team_multisig}).setSignerAddress(signer_address)

    assert contract.call().owner() == team_multisig
    return contract


@pytest.fixture
def customer(accounts) -> str:
    """Get a customer address."""
    return to_checksum_address(accounts[1])


@pytest.fixture
def pricing_info() -> int:
    """Use this same pricingInfo, which is a tier indentifier in this case."""
    return 123


@pytest.fixture
def customer_id(uncapped_flatprice, uncapped_flatprice_finalizer, team_multisig) -> int:
    """Generate UUID v4 customer id as a hex string."""
    customer_id = uuid.uuid4()
    return customer_id


@pytest.fixture
def pad_contract(chain):
    """Token contract we are buying."""
    contract, hash = chain.provider.deploy_contract('TestSolidityAddressHash')
    return contract


def test_kyc_participate_with_signed_address(chain, web3, kyc_presale, customer, customer_id, private_key, preico_starts_at, team_multisig, pricing_info, signer_address):
    """Buy tokens with a proper KYC payload."""

    # Check KYC crowdsale is good to go
    time_travel(chain, kyc_presale.call().startsAt() + 1)

    # No contributions yet
    original_multisig_balance = web3.eth.getBalance(team_multisig)

    # Check the setup looks good
    assert kyc_presale.call().getState() == CrowdsaleState.Funding
    assert kyc_presale.call().signerAddress().lower() == signer_address.lower()

    # Do a test buy for 0.5 ETH and check it is good token wise
    wei_value = to_wei(1.0, "ether")

    # KYC limits for this participant: 0...1 ETH
    kyc_payload = pack_kyc_pricing_dataframe(customer, customer_id, 0, 1 * 10000, pricing_info)
    signed_data = sign(kyc_payload, private_key)

    kyc_presale.transact({"from": customer, "value": wei_value, "gas": 2222333}).buyWithKYCData(kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"])

    # Money lands in the multisig wallet
    assert kyc_presale.call().investedAmountOf(customer) == 1 * 10**18
    assert web3.eth.getBalance(team_multisig) > original_multisig_balance

    # We have tracked the investor id
    events = kyc_presale.pastEvents("Prepurchased").get()
    assert len(events) == 1
    e = events[0]
    assert e["args"]["investor"].lower() == customer.lower()
    assert e["args"]["weiAmount"] == wei_value
    assert e["args"]["customerId"] == customer_id.int
    assert e["args"]["pricingInfo"] == pricing_info


def test_kyc_participate_bad_signature(chain, kyc_presale, customer, customer_id, private_key, preico_starts_at, team_multisig, pricing_info):
    """Investment does not happen with a bad signature.."""

    # Check KYC crowdsale is good to go
    time_travel(chain, kyc_presale.call().startsAt() + 1)

    # Do a test buy for 1 ETH and check it is good token wise
    wei_value = to_wei(1, "ether")

    # KYC limits for this participant: 0...1 ETH
    kyc_payload = pack_kyc_pricing_dataframe(customer, customer_id, 0, 1 * 10000, pricing_info)
    signed_data = sign(kyc_payload, private_key + "x")  # Use bad private key

    with pytest.raises(TransactionFailed):
        kyc_presale.transact({"from": customer, "value": wei_value, "gas": 2222333}).buyWithKYCData(kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"])


def test_kyc_participate_under_payment(chain, kyc_presale, customer, customer_id, private_key, preico_starts_at, team_multisig, pricing_info):
    """KYC'ed participant does not fulfill his minimum limit."""

    # Check KYC crowdsale is good to go
    time_travel(chain, kyc_presale.call().startsAt() + 1)

    # Do a test buy for 1 ETH and check it is good token wise
    wei_value = to_wei(0.1, "ether")

    # KYC limits for this participant: 0...1 ETH
    kyc_payload = pack_kyc_pricing_dataframe(customer, customer_id, int(0.5 * 10000), 1 * 10000, pricing_info)
    signed_data = sign(kyc_payload, private_key)  # Use bad private key

    with pytest.raises(TransactionFailed):
        kyc_presale.transact({"from": customer, "value": wei_value, "gas": 2222333}).buyWithKYCData(kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"])


def test_kyc_participate_over_payment(chain, kyc_presale, customer, customer_id, private_key, preico_starts_at, team_multisig, pricing_info):
    """KYC'ed participant does not fulfill his minimum limit."""

    # Check KYC crowdsale is good to go
    time_travel(chain, kyc_presale.call().startsAt() + 1)

    wei_value = to_wei(1, "ether")

    # KYC limits for this participant: 0...1 ETH
    kyc_payload = pack_kyc_pricing_dataframe(customer, customer_id, 0, 10 * 10000, pricing_info)
    signed_data = sign(kyc_payload, private_key)  # Use bad private key

    kyc_presale.transact({"from": customer, "value": wei_value, "gas": 2222333}).buyWithKYCData(kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"])

    with pytest.raises(TransactionFailed):
        wei_value = to_wei(10, "ether")
        kyc_presale.transact({"from": customer, "value": wei_value, "gas": 2222333}).buyWithKYCData(kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"])


def test_kyc_participate_set_signer_only_owner(chain, kyc_presale, malicious_address, signer_address):
    """Only owner can set the KYC signing key."""

    with pytest.raises(TransactionFailed):
        kyc_presale.transact({"from": malicious_address}).setSignerAddress(signer_address)


def test_kyc_participate_whitelist(chain, kyc_presale, customer, customer_id, private_key, preico_starts_at, team_multisig, pricing_info):
    """Early whitelist buyer gets through despite time checks."""

    # Check KYC crowdsale is closed, too early
    time_travel(chain, kyc_presale.call().startsAt() - 1)
    assert kyc_presale.call().getState() == CrowdsaleState.PreFunding

    # Do a test buy for 1 ETH and check it is good token wise
    wei_value = to_wei(1, "ether")

    # KYC limits for this participant: 0...1 ETH
    kyc_payload = pack_kyc_pricing_dataframe(customer, customer_id, 0, 1 * 10000, pricing_info)
    signed_data = sign(kyc_payload, private_key)

    with pytest.raises(TransactionFailed):
        kyc_presale.transact({"from": customer, "value": wei_value, "gas": 2222333}).buyWithKYCData(kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"])

    # Whitelist this participant
    kyc_presale.transact({"from": team_multisig}).setEarlyParicipantWhitelist(customer, True)

    # Now we can buy despite the time limti
    kyc_presale.transact({"from": customer, "value": wei_value, "gas": 2222333}).buyWithKYCData(kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"])


def test_new_cap(chain, kyc_presale, customer, customer_id, private_key, preico_starts_at, team_multisig, pricing_info):
    """We can set a new cap correctly."""

    assert kyc_presale.call().saleWeiCap() == 99999 * 10**18
    kyc_presale.transact({"from": team_multisig}).setWeiCap(200 * 10**18)
    assert kyc_presale.call().saleWeiCap() == 200 * 10**18


def test_new_cap_only_owner(chain, kyc_presale, customer, customer_id, private_key, preico_starts_at, team_multisig, pricing_info):
    """Only owner can set the new cap.."""

    assert kyc_presale.call().saleWeiCap() == 99999 * 10**18
    with pytest.raises(TransactionFailed):
        kyc_presale.transact({"from": customer}).setWeiCap(200 * 10**18)


def test_halted(chain, web3, kyc_presale, customer, customer_id, private_key, preico_starts_at, team_multisig, pricing_info, signer_address):
    """We cannot buy after a halt."""

    # Check KYC crowdsale is good to go
    time_travel(chain, kyc_presale.call().startsAt() + 1)

    # Check the setup looks good
    assert kyc_presale.call().getState() == CrowdsaleState.Funding
    assert kyc_presale.call().signerAddress().lower() == signer_address.lower()

    # Do a test buy for 0.5 ETH and check it is good token wise
    wei_value = to_wei(1.0, "ether")

    # KYC limits for this participant: 0...1 ETH
    kyc_payload = pack_kyc_pricing_dataframe(customer, customer_id, 0, 1 * 10000, pricing_info)
    signed_data = sign(kyc_payload, private_key)

    kyc_presale.transact({"from": team_multisig}).halt()

    with pytest.raises(TransactionFailed):
        kyc_presale.transact({"from": customer, "value": wei_value, "gas": 2222333}).buyWithKYCData(kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"])

