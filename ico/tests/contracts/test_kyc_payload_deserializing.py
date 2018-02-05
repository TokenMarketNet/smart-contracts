import uuid

import pytest
from eth_utils import to_normalized_address, to_checksum_address
from web3.contract import Contract

from ico.kyc import pack_kyc_dataframe
from ico.kyc import pack_kyc_pricing_dataframe


@pytest.fixture()
def kyc_deserializer(chain, presale_crowdsale, uncapped_token, team_multisig) -> Contract:
    """Set crowdsale end strategy."""

    # Create finalizer contract
    args = []
    contract, hash = chain.provider.deploy_contract('KYCPayloadDeserializer', deploy_args=args)
    return contract


@pytest.fixture()
def whitelisted_address(accounts):
    return to_checksum_address(accounts[0])


def test_roundtrip_kyc_data(kyc_deserializer, whitelisted_address):
    """We correctly encode data in Python side and decode it back in the smart contract."""

    customer_id = uuid.uuid4()
    dataframe = pack_kyc_dataframe(whitelisted_address, customer_id, int(0.1 * 10000), int(9999 * 10000))
    tuple_value = kyc_deserializer.call().getKYCPayload(dataframe)

    #
    # Check that the output looks like what we did expect
    #

    assert tuple_value[0].lower() == whitelisted_address.lower()
    # Do a raw integer comparison, because web3.py and UUID disagree about left padding zeroes
    assert tuple_value[1] == customer_id.int
    assert tuple_value[2] == 1000
    assert tuple_value[3] == 99990000

def test_roundtrip_kyc_presale_data(kyc_deserializer, whitelisted_address):
    """We correctly encode data in Python side and decode it back in the smart contract."""

    customer_id = uuid.uuid4()
    dataframe = pack_kyc_pricing_dataframe(whitelisted_address, customer_id, int(0.1 * 10000), int(9999 * 10000), 123)
    tuple_value = kyc_deserializer.call().getKYCPresalePayload(dataframe)

    #
    # Check that the output looks like what we did expect
    #

    assert tuple_value[0].lower() == whitelisted_address.lower()
    # Do a raw integer comparison, because web3.py and UUID disagree about left padding zeroes
    assert tuple_value[1] == customer_id.int
    assert tuple_value[2] == 1000
    assert tuple_value[3] == 99990000
    assert tuple_value[4] == 123
