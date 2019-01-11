"""Signed address investing."""

import uuid

import pytest

from eth_tester.exceptions import TransactionFailed
from eth_utils import to_wei
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.state import CrowdsaleState
from ico.sign import get_ethereum_address_from_private_key
from ico.sign import sign
from ico.kyc import pack_kyc_pricing_dataframe, unpack_kyc_pricing_dataframe


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
def kyc_token(chain, team_multisig, initial_supply):
    """Create the token contract."""

    args = ["KYC token", "KYC", initial_supply, 18, True]  # Owner set

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('CrowdsaleToken', deploy_args=args, deploy_transaction=tx)
    return contract


@pytest.fixture
def pricing(chain, preico_token_price) -> Contract:
    """1 ETH = 1 token"""
    args = [
        1*10**18,
    ]
    pricing_strategy, hash = chain.provider.deploy_contract('FlatPricing', deploy_args=args)
    return pricing_strategy


@pytest.fixture
def kyc_crowdsale(chain, team_multisig, preico_starts_at, preico_ends_at, pricing, preico_cap, preico_funding_goal, preico_token_allocation, kyc_token, signer_address, default_finalize_agent, initial_supply) -> Contract:
    """Create a Pre-ICO crowdsale contract."""

    token = kyc_token

    args = [
        token.address,
        pricing.address,
        team_multisig,
        preico_starts_at,
        preico_ends_at,
        preico_funding_goal,
        team_multisig
    ]

    tx = {
        "from": team_multisig,
    }

    contract, hash = chain.provider.deploy_contract('KYCCrowdsale', deploy_args=args, deploy_transaction=tx)

    args = [
        contract.address
    ]
    finalizer_contract, hash = chain.provider.deploy_contract('NullFinalizeAgent', deploy_args=args)
    contract.functions.setFinalizeAgent(finalizer_contract.address).transact({"from": team_multisig})

    assert contract.functions.owner().call() == team_multisig
    assert not token.functions.released().call()

    # Allow the token sale contract to distribute unreleased tokens
    # token.transact({"from": team_multisig}).setTransferAgent(contract.address, True)
    token.functions.setTransferAgent(team_multisig, True).transact({"from": team_multisig})
    token.functions.approve(contract.address, initial_supply).transact({"from": team_multisig})
    token.functions.setReleaseAgent(team_multisig).transact({"from": team_multisig})
    contract.functions.setSignerAddress(signer_address).transact({"from": team_multisig})
    return contract


@pytest.fixture
def customer(accounts) -> str:
    """Get a customer address."""
    return accounts[1]


@pytest.fixture
def customer_id(uncapped_flatprice, uncapped_flatprice_finalizer, team_multisig) -> uuid.uuid4:
    """Generate UUID v4 customer id as a hex string."""
    customer_id = uuid.uuid4()
    return customer_id


@pytest.fixture
def pad_contract(chain):
    """Token contract we are buying."""
    contract, hash = chain.provider.deploy_contract('TestSolidityAddressHash')
    return contract


def test_kyc_participate_with_signed_address(chain, kyc_crowdsale, customer, customer_id, kyc_token, private_key, preico_starts_at, pricing, team_multisig):
    """Buy tokens with a proper KYC payload."""

    # Check KYC crowdsale is good to go
    time_travel(chain, kyc_crowdsale.call().startsAt() + 1)
    event_filter = kyc_crowdsale.events.Invested().createFilter(fromBlock=0)
    # Check the setup looks good
    assert kyc_crowdsale.functions.getState().call() == CrowdsaleState.Funding
    assert kyc_crowdsale.functions.isFinalizerSane().call()
    assert kyc_crowdsale.functions.isPricingSane().call()
    assert kyc_crowdsale.functions.beneficiary().call() == team_multisig
    assert kyc_token.functions.transferAgents(team_multisig).call() == True

    # Do a test buy for 1 ETH and check it is good token wise
    wei_value = to_wei(1, "ether")
    tokens_per_eth = pricing.functions.calculatePrice(wei_value, wei_value, 0, customer, 18).call()
    assert tokens_per_eth == 10**18
    assert kyc_crowdsale.functions.getTokensLeft().call() >= tokens_per_eth
    assert kyc_token.functions.balanceOf(team_multisig).call() >= tokens_per_eth
    assert not kyc_crowdsale.functions.isBreakingCap(wei_value, tokens_per_eth, wei_value, tokens_per_eth).call()

    # KYC limits for this participant: 0...1 ETH
    kyc_payload = pack_kyc_pricing_dataframe(customer, customer_id, 0, 1*10000, 1*10**18)
    signed_data = sign(kyc_payload, private_key)

    kyc_crowdsale.functions.buyWithKYCData(
        kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"]
    ).transact({"from": customer, "value": wei_value})
    # We got credited
    assert kyc_token.functions.balanceOf(customer).call() > 0
    assert kyc_crowdsale.functions.investedAmountOf(customer).call() == 1 * 10**18

    # We have tracked the investor id
    events = event_filter.get_all_entries()
    assert len(events) == 1
    e = events[0]
    assert e["args"]["investor"] == customer
    assert e["args"]["weiAmount"] == wei_value
    assert e["args"]["customerId"] == customer_id.int


def test_kyc_participate_bad_signature(chain, kyc_crowdsale, customer, customer_id, kyc_token, private_key, preico_starts_at, pricing, team_multisig):
    """Investment does not happen with a bad signature.."""

    # Check KYC crowdsale is good to go
    time_travel(chain, kyc_crowdsale.call().startsAt() + 1)

    # Do a test buy for 1 ETH and check it is good token wise
    wei_value = to_wei(1, "ether")

    # KYC limits for this participant: 0...1 ETH
    kyc_payload = pack_kyc_pricing_dataframe(customer, customer_id, 0, 1*10000, 1)
    signed_data = sign(kyc_payload, private_key + "x")  # Use bad private key

    with pytest.raises(TransactionFailed):
        kyc_crowdsale.functions.buyWithKYCData(
            kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"]
        ).transact({"from": customer, "value": wei_value})


def test_kyc_participate_under_payment(chain, kyc_crowdsale, customer, customer_id, kyc_token, private_key, preico_starts_at, pricing, team_multisig):
    """KYC'ed participant does not fulfill his minimum limit."""

    # Check KYC crowdsale is good to go
    time_travel(chain, kyc_crowdsale.call().startsAt() + 1)

    # Do a test buy for 1 ETH and check it is good token wise
    wei_value = to_wei(0.1, "ether")

    # KYC limits for this participant: 0...1 ETH
    kyc_payload = pack_kyc_pricing_dataframe(customer, customer_id, int(0.5 * 10000), 1*10000, 1)
    signed_data = sign(kyc_payload, private_key)  # Use bad private key

    with pytest.raises(TransactionFailed):
        kyc_crowdsale.functions.buyWithKYCData(
            kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"]
        ).transact({"from": customer, "value": wei_value})


def test_kyc_participate_over_payment(chain, kyc_crowdsale, customer, customer_id, kyc_token, private_key, preico_starts_at, pricing, team_multisig):
    """KYC'ed participant does not fulfill his minimum limit."""

    # Check KYC crowdsale is good to go
    time_travel(chain, kyc_crowdsale.call().startsAt() + 1)

    wei_value = to_wei(1, "ether")

    # KYC limits for this participant: 0...1 ETH
    kyc_payload = pack_kyc_pricing_dataframe(customer, customer_id, 0, 10*10000, 1*10**18)
    signed_data = sign(kyc_payload, private_key)  # Use bad private key

    kyc_crowdsale.functions.buyWithKYCData(
        kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"]
    ).transact({"from": customer, "value": wei_value})

    with pytest.raises(TransactionFailed):
        wei_value = to_wei(10, "ether")
        kyc_crowdsale.functions.buyWithKYCData(
            kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"]
        ).transact({"from": customer, "value": wei_value})


def test_kyc_participate_set_signer_only_owner(chain, kyc_crowdsale, malicious_address, signer_address):
    """Only owner can set the KYC signing key."""

    with pytest.raises(TransactionFailed):
        kyc_crowdsale.functions.setSignerAddress(signer_address).transact({"from": malicious_address})


def test_kyc_participate_with_different_price(chain, web3, kyc_crowdsale, customer, customer_id, kyc_token, private_key, preico_starts_at, pricing, team_multisig):
    """The same user buys token with two different prices (as given by the server)."""

    # Check KYC crowdsale is good to go
    whitelisted_address = customer
    time_travel(chain, kyc_crowdsale.call().startsAt() + 1)
    start_multisig_total = web3.eth.getBalance(team_multisig)
    events_filter = kyc_crowdsale.events.Invested().createFilter(fromBlock=0)
    # Check the setup looks good
    assert kyc_crowdsale.functions.getState().call() == CrowdsaleState.Funding
    assert kyc_crowdsale.functions.isFinalizerSane().call()
    assert kyc_crowdsale.functions.isPricingSane().call()
    assert kyc_crowdsale.functions.beneficiary().call() == team_multisig
    assert kyc_token.functions.transferAgents(team_multisig).call() == True
    assert kyc_crowdsale.functions.investedAmountOf(whitelisted_address).call() == 0

    # Do a test buy for 1 ETH
    wei_value = to_wei(1, "ether")
    excepted_token_value = int(0.5 * 10**18)
    price = 2*10**18  # wei per token

    assert kyc_crowdsale.call().calculateTokens(wei_value, price) == excepted_token_value

    # Buy with price 1 token = 2 wei
    kyc_payload = pack_kyc_pricing_dataframe(whitelisted_address, customer_id, 0, 1*10000, price)
    signed_data = sign(kyc_payload, private_key)
    unpacked = unpack_kyc_pricing_dataframe(kyc_payload)
    assert unpacked["pricing_data"] == price

    kyc_crowdsale.functions.buyWithKYCData(
        kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"]
    ).transact({"from": whitelisted_address, "value": wei_value})

    # We got credited
    assert kyc_token.functions.balanceOf(whitelisted_address).call() == excepted_token_value
    assert kyc_crowdsale.functions.investedAmountOf(whitelisted_address).call() == wei_value

    # We have tracked the investor id
    events = events_filter.get_new_entries()
    assert len(events) == 1
    e = events[0]
    assert e["args"]["investor"] == whitelisted_address
    assert e["args"]["weiAmount"] == wei_value
    assert e["args"]["customerId"] == customer_id.int
    assert e["args"]["tokenAmount"] == excepted_token_value

    # More tokens, different price this time
    wei_value = to_wei(1, "ether")
    new_excepted_token_value = int(0.25 * 10**18)
    price = 4*10**18 # wei per token

    # New transaction, increased per person cap to 2 ETH
    kyc_payload = pack_kyc_pricing_dataframe(whitelisted_address, customer_id, 0, 2*10000, price)
    signed_data = sign(kyc_payload, private_key)
    kyc_crowdsale.functions.buyWithKYCData(
        kyc_payload, signed_data["v"], signed_data["r_bytes"], signed_data["s_bytes"]
    ).transact({"from": whitelisted_address, "value": wei_value})

    # We got credited
    total = wei_value * 2
    assert kyc_token.functions.balanceOf(whitelisted_address).call() == excepted_token_value + new_excepted_token_value
    assert kyc_crowdsale.functions.investedAmountOf(whitelisted_address).call() == total
    assert web3.eth.getBalance(team_multisig) == start_multisig_total + total

    # We have another event, this time with new price
    events = events_filter.get_new_entries()
    assert len(events) == 1
    e = events[-1]
    assert e["args"]["investor"] == whitelisted_address
    assert e["args"]["weiAmount"] == wei_value
    assert e["args"]["customerId"] == customer_id.int
    assert e["args"]["tokenAmount"] == new_excepted_token_value
