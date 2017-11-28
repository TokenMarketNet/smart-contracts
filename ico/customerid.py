"""Customer id checksum tools."""
from uuid import UUID

from sha3 import keccak_256
from rlp.utils import decode_hex


def calculate_customer_id_checksum_byte(customer_id: UUID) -> int:
    """Calculate the checksum byte.

    The checksum byte prevents invalid data field copy-pastes (pasting in partial customer id).
    This is because EVM does not have built in mechanism to detect invalid contract function transaction call payload.

    This is used in PaymentForwarder and Crowdsale.

    :param customer_id: UUID (u128 int) customer id
    :return: The value of the checksum byte
    """

    customer_id = int(customer_id.hex, 16)  # Customer ids are 128-bit UUID v4
    checksum_byte = keccak_256(decode_hex(format(customer_id, 'x').zfill(32))).digest()[:1]
    return checksum_byte
