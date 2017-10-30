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
    bytes32 = deserializer.call().getBytes32(encoded_payload, 0x00)
    assert bytes32 =='\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'


def test_decode_uint256(deserializer):
    """We correctly deserializer various uint32 bytes values."""


    # Test different values
    # 0x01
    # 0x0100
    # 0x010000
    # ...
    for i in range(31):
        payload = 0x01 << (8*i)
        encoded_payload = payload.to_bytes(32, byteorder='big')
        value = deserializer.call().getUint256(encoded_payload, 0x00)
        assert value == payload, "Did not deserializer correctly: {} {}".format(payload, encoded_payload)


def test_offset_uint256(deserializer):
    """We correctly deserializer uint32 from different offsets."""

    for i in range(31):
        offset = b"\x00" * i
        payload = 0x01 << (8*i)
        encoded_payload = offset + payload.to_bytes(32, byteorder='big')
        value = deserializer.call().getUint256(encoded_payload, i)
        assert value == payload, "Did not deserializer correctly: {} {}".format(payload, encoded_payload)
