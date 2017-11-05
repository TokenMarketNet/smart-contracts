"""Signed address investing."""

import uuid

import binascii
import bitcoin
import pytest
from eth_utils import force_bytes
from ethereum.tester import TransactionFailed
from eth_utils import to_wei
from web3.contract import Contract

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
def kyc_token(token):
    """Token contract we are buying."""
    return token

@pytest.fixture
def kyc_crowdsale(chain, team_multisig, preico_starts_at, preico_ends_at, flat_pricing, preico_cap, preico_funding_goal, preico_token_allocation, kyc_token, signer_address, default_finalize_agent) -> Contract:
    """Create a Pre-ICO crowdsale contract."""

    token = kyc_token

    args = [
        token.address,
        flat_pricing.address,
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
    contract.transact({"from": team_multisig}).setFinalizeAgent(finalizer_contract.address)

    assert contract.call().owner() == team_multisig
    assert not token.call().released()

    # Allow pre-ico contract to do mint()
    token.transact({"from": team_multisig}).setMintAgent(contract.address, True)
    token.transact({"from": team_multisig}).setReleaseAgent(finalizer_contract.address)

    assert token.call().mintAgents(contract.address) == True

    # This is not available in KYCCrowdsale, is this intentional?
    contract.transact({"from": team_multisig}).setRequireSignedAddress(True, signer_address)
    return contract


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

def test_kyc_participate_with_signed_address(chain, kyc_crowdsale, customer, customer_id, kyc_token, private_key, preico_starts_at):
    """Buy tokens with a proper signed address."""

    address_bytes = get_address_as_bytes(customer)
    sign_data = sign(address_bytes, private_key)

    time_travel(chain, kyc_crowdsale.call().startsAt() + 1)
    wei_value = to_wei(1, "ether")
    assert kyc_crowdsale.call().getState() == CrowdsaleState.Funding
    kyc_crowdsale.transact({"from": customer, "value": wei_value}).buyWithKYCData(customer_id, sign_data["v"], sign_data["r_bytes"], sign_data["s_bytes"])

    # We got credited
    assert kyc_token.call().balanceOf(customer) > 0

    # We have tracked the investor id
    events = kyc_crowdsale.pastEvents("Invested").get()
    assert len(events) == 1
    e = events[0]
    assert e["args"]["investor"] == customer
    assert e["args"]["weiAmount"] == wei_value
    assert e["args"]["customerId"] == customer_id


def test_kyc_participate_bad_signature(chain, kyc_crowdsale, customer, customer_id, kyc_token):
    """Investment does not happen with a bad signature.."""

    address_bytes = get_address_as_bytes(customer)
    sign_data = sign(address_bytes, private_key)

    time_travel(chain, kyc_crowdsale.call().startsAt() + 1)
    wei_value = to_wei(1, "ether")
    assert kyc_crowdsale.call().getState() == CrowdsaleState.Funding

    sign_data["s_bytes"] = b'ABC'  # Corrupt signature data

    with pytest.raises(TransactionFailed):
        kyc_crowdsale.transact({"from": customer, "value": wei_value}).buyWithSignedAddress(customer_id, sign_data["v"], sign_data["r_bytes"], sign_data["s_bytes"])


def test_kyc_left_pad(pad_contract):
    """Ensure we handle leading zero in the address correctly."""

    address_bytes = get_address_as_bytes(pad_contract.call().leftPad())
    hash = bitcoin.bin_sha256(address_bytes)
    val = pad_contract.call().getHashLeftPad()
    val = force_bytes(val)
    assert hash == val


@pytest.mark.skip(reason="Solidity compiler 0.4.11 does not run this yet")
def test_kyc_right_pad(pad_contract):
    """Ensure we handle trailing zero in the address correctly."""

    address_bytes = get_address_as_bytes(pad_contract.call().rightPad())
    hash = bitcoin.bin_sha256(address_bytes)
    val = pad_contract.call().getHashRightPad()
    val = force_bytes(val)
    assert hash == val
