import pytest
from web3.contract import Contract


@pytest.fixture()
def deserializer(chain, presale_crowdsale, uncapped_token, team_multisig) -> Contract:
    """Set crowdsale end strategy."""

    # Create finalizer contract
    args = []
    contract, hash = chain.provider.deploy_contract('TestBytesDeserializer', deploy_args=args)
    return contract


def test_decode_bytes32(deserializer):
    """We correctly get bytes 32 back."""
    encoded_payload = 0x01.to_bytes(32, byteorder='little')
    bytes32 = deserializer.functions.getBytes32(encoded_payload, 0x00).call()
    assert bytes32 == b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'


def test_decode_uint256(deserializer):
    """We correctly deserializer various uint256 bytes values."""


    # Test different values
    # 0x01
    # 0x0100
    # 0x010000
    # ...
    for i in range(31):
        payload = 0x01 << (8*i)
        encoded_payload = payload.to_bytes(32, byteorder='big')
        value = deserializer.functions.getUint256(encoded_payload, 0x00).call()
        assert value == payload, "Did not deserializer correctly: {} {}".format(payload, encoded_payload)


def test_offset_uint256(deserializer):
    """We correctly deserializer uint256 from different offsets."""

    for i in range(31):
        offset = b"\x00" * i
        payload = 0x01 << (8*i)
        encoded_payload = offset + payload.to_bytes(32, byteorder='big')
        value = deserializer.functions.getUint256(encoded_payload, i).call()
        assert value == payload, "Did not deserializer correctly: {} {}".format(payload, encoded_payload)


def test_decode_uint128(deserializer):
    """We correctly deserializer various uint128 bytes values."""

    for i in range(15):
        payload = 0x01 << (8*i)
        encoded_payload = payload.to_bytes(16, byteorder='big')
        value = deserializer.functions.getUint128(encoded_payload, 0x00).call()
        assert value == payload, "Did not deserializer correctly: {} {}".format(payload, encoded_payload)


def test_decode_uint16(deserializer):
    """We correctly deserializer various uint32 bytes values."""

    for i in range(2):
        payload = 0x01 << (8*i)
        encoded_payload = payload.to_bytes(2, byteorder='big')
        value = deserializer.functions.getUint16(encoded_payload, 0x00).call()
        assert value == payload, "Did not deserializer correctly: {} {}".format(payload, encoded_payload)


def test_decode_uint32(deserializer):
    """We correctly deserializer various uint32 bytes values."""

    for i in range(2):
        payload = 0x01 << (8*i)
        encoded_payload = payload.to_bytes(2, byteorder='big')
        value = deserializer.functions.getUint16(encoded_payload, 0x00).call()
        assert value == payload, "Did not deserializer correctly: {} {}".format(payload, encoded_payload)


def test_decode_address(deserializer):
    """We correctly deserializer Ethereum addresses."""
    address = "0x82A978B3f5962A5b0957d9ee9eEf472EE55B42F1"

    addr_value = int(address, 16)
    addr_b = addr_value.to_bytes(20, byteorder="big")  # Ethereum address is 20 bytes
    value = deserializer.functions.getAddress(addr_b, 0).call()
    assert value == address, "Did not deserializer correctly: {} {}".format(value, address)
