"""AML data passing helpers."""
from binascii import hexlify
from uuid import UUID

from eth_utils import is_checksum_address


def pack_kyc_dataframe(whitelisted_address: str, customer_id: UUID, min_eth_10k: int, max_eth_10k: int) -> bytes:
    """Pack KYC information to the smart contract.

    See KYCPayloadDeserializer for the matching Solidity code.

    .. note ::

        In a long term this will be deprecated in the behalf of  the function below.

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


def pack_kyc_pricing_dataframe(whitelisted_address: str, customer_id: UUID, min_eth_10k: int, max_eth_10k: int, pricing_info: int) -> bytes:
    """Pack KYC presale information to the smart contract.

    Same as above, but with pricing info included.

    See KYCPayloadDeserializer for the matching Solidity code.

    :param whitelisted_address: Must be whitelisted address in a Ethereum checksummed format
    :param customer_id: Customer id as UUIDv8
    :param min_eth: Min investment for this customer. Expressed as the parts of 1/10000.
    :param max_eth: Max investment for this customer. Expressed as the parts of 1/10000.
    :param pricing_info: Tier identifier or directly one token price in wei.
    :return: Raw bytes to send to the contract as a function argument
    """
    assert is_checksum_address(whitelisted_address)
    assert isinstance(customer_id, UUID)
    assert type(min_eth_10k) == int
    assert type(max_eth_10k) == int
    assert type(pricing_info) == int
    addr_value = int(whitelisted_address, 16)
    addr_b = addr_value.to_bytes(20, byteorder="big")  # Ethereum address is 20 bytes
    customer_b = customer_id.bytes
    min_b = min_eth_10k.to_bytes(4, byteorder="big")
    max_b = max_eth_10k.to_bytes(4, byteorder="big")
    pricing_data = pricing_info.to_bytes(32, byteorder="big")
    data = addr_b + customer_b + min_b + max_b + pricing_data
    assert len(data) == 76, "Got length: {}".format(len(data))
    return data


def unpack_kyc_pricing_dataframe(b: bytes) -> dict:
    """Unpack a KYC payloda for diagnostics purposes.

    Useful to troubleshoot live transactions. Grab the transaction hex data from Etherscan, starting on [5], make it a single string and use this function to see what parameters where given to the user.

    Example::

        import binascii
        from ico.kyc import unpack_kyc_pricing_dataframe

        h = "83dcb...40000000000000000000000000000000000000000000000000000000000000001"
        b = binascii.unhexlify(h)
        unpack_kyc_pricing_dataframe(b)

    """

    assert len(b) == 76, "Got byte array of length: {}".format(len(b))
    addr_value = b[0:20]
    customer_id = b[20:36]
    min_b = b[36:40]
    max_b = b[40:44]
    pricing_data = b[44:76]

    return {
        "address": "0x" + hexlify(addr_value).decode("ascii"),
        "customer_id": UUID(int=int(hexlify(customer_id), 16)),
        "min_payment_eth": int(hexlify(min_b), 16) / 10000.0,
        "max_payment_eth": int(hexlify(max_b), 16) / 10000.0,
        "pricing_data": int(hexlify(pricing_data), 16),
    }
