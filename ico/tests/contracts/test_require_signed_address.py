"""Signed address investing."""

import uuid

import bitcoin
import pytest
from eth_utils import to_bytes
from eth_tester.exceptions import TransactionFailed
from eth_utils import to_wei

from ico.tests.utils import time_travel
from ico.state import CrowdsaleState
from ico.sign import get_ethereum_address_from_private_key
from ico.sign import get_address_as_bytes
from ico.sign import sign


@pytest.fixture
def private_key():
    """Server side private key."""
    return "Toholampi summer festival 2017 has the most harcore rock bands"


@pytest.fixture
def signer_address(private_key):
    """Server side signer address."""
    return get_ethereum_address_from_private_key(private_key)


@pytest.fixture
def crowdsale(uncapped_flatprice, uncapped_flatprice_finalizer, team_multisig, signer_address):
    """Set up a crowdsale with customer id require policy."""
    uncapped_flatprice.functions.setRequireSignedAddress(True, signer_address).transact({"from": team_multisig})
    return uncapped_flatprice


@pytest.fixture
def token(uncapped_token):
    """Token contract we are buying."""
    return uncapped_token


@pytest.fixture
def customer_id(uncapped_flatprice, uncapped_flatprice_finalizer, team_multisig) -> int:
    """Generate UUID v4 customer id as a hex string."""
    customer_id = int(uuid.uuid4().hex, 16)  # Customer ids are 128-bit UUID v4
    return customer_id


@pytest.fixture
def pad_contract(chain):
    """Token contract we are buying."""
    contract, hash = chain.provider.deploy_contract('TestSolidityAddressHash')
    return contract


def test_only_owner_change_change_policy(crowdsale, customer, signer_address):
    """Only owner change change customerId required policy."""

    with pytest.raises(TransactionFailed):
        crowdsale.functions.setRequireSignedAddress(True, signer_address).transact({"from": customer})


def test_participate_with_signed_address(chain, crowdsale, customer, customer_id, token, private_key):
    """Buy tokens with a proper signed address."""

    address_bytes = get_address_as_bytes(customer)
    sign_data = sign(address_bytes, private_key)

    time_travel(chain, crowdsale.functions.startsAt().call() + 1)
    wei_value = to_wei(1, "ether")
    assert crowdsale.functions.getState().call() == CrowdsaleState.Funding
    crowdsale.functions.buyWithSignedAddress(
        customer_id, sign_data["v"], sign_data["r_bytes"], sign_data["s_bytes"]
    ).transact({"from": customer, "value": wei_value})

    # We got credited
    assert token.functions.balanceOf(customer).call() > 0

    # We have tracked the investor id
    events = crowdsale.events.Invested().createFilter(fromBlock=0).get_all_entries()
    assert len(events) == 1
    e = events[0]
    assert e["args"]["investor"] == customer
    assert e["args"]["weiAmount"] == wei_value
    assert e["args"]["customerId"] == customer_id


def test_participate_bad_signature(chain, crowdsale, customer, customer_id, token, private_key):
    """Investment does not happen with a bad signature.."""

    address_bytes = get_address_as_bytes(customer)
    sign_data = sign(address_bytes, private_key)

    time_travel(chain, crowdsale.functions.startsAt().call() + 1)
    wei_value = to_wei(1, "ether")
    assert crowdsale.functions.getState().call() == CrowdsaleState.Funding

    sign_data["s_bytes"] = b'ABC'  # Corrupt signature data

    with pytest.raises(TransactionFailed):
        crowdsale.functions.buyWithSignedAddress(
            customer_id, sign_data["v"], sign_data["r_bytes"], sign_data["s_bytes"]
        ).transact({"from": customer, "value": wei_value})


def test_left_pad(pad_contract):
    """Ensure we handle leading zero in the address correctly."""

    address_bytes = get_address_as_bytes(pad_contract.functions.leftPad().call())
    hash = bitcoin.bin_sha256(address_bytes)
    val = pad_contract.functions.getHashLeftPad().call()
    val = to_bytes(val)
    assert hash == val


@pytest.mark.skip(reason="Solidity compiler 0.4.11 does not run this yet")
def test_right_pad(pad_contract):
    """Ensure we handle trailing zero in the address correctly."""

    address_bytes = get_address_as_bytes(pad_contract.functions.rightPad().call())
    hash = bitcoin.bin_sha256(address_bytes)
    val = pad_contract.functions.getHashRightPad().call()
    val = to_bytes(val)
    assert hash == val
