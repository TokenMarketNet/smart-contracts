"""AML data passing helpers."""
from uuid import UUID

from eth_utils import is_checksum_address


def pack_kyc_dataframe(whitelisted_address: str, customer_id: UUID, min_eth_10k: int, max_eth_10k: int) -> bytes:
    """Pack KYC information to the smart contract.

    See KYCPayloadDeserializer for the matching Solidity code.

    :param whitelisted_address: Must be whitelisted address in a Ethereum checksummed format
    :param customer_id: Customer id as UUIDv8
    :param min_eth: Min investment for this customer. Expressed as the parts of 1/10000.
    :param max_eth: Max investment for this customer. Expressed as the parts of 1/10000.
    :return:
    """
    assert is_checksum_address(whitelisted_address)
    assert isinstance(customer_id, UUID)
    assert type(min_eth_10k) == int
    assert type(max_eth_10k) == int
    addr_value = int(whitelisted_address, 16)
    addr_b = addr_value.to_bytes(20, byteorder="big")  # Ethereum address is 20 bytes
    customer_b = customer_id.bytes
    min_b = min_eth_10k.to_bytes(4, byteorder="big")
    max_b = max_eth_10k.to_bytes(4, byteorder="big")
    data = addr_b + customer_b + min_b + max_b
    assert len(data) == 44, "Got length: {}".format(len(data))
    return data
