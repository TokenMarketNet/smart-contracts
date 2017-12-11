"""Sign data with Ethereum private key."""
import binascii

import bitcoin
from eth_utils import pad_left
from ethereum import utils
from ethereum.utils import big_endian_to_int, sha3
from secp256k1 import PrivateKey


def get_ethereum_address_from_private_key(private_key_seed_ascii: str) -> str:
    """Generate Ethereum address from a private key.

    https://github.com/ethereum/pyethsaletool/blob/master/pyethsaletool.py#L111

    :param private_key: Any string as a seed

    :return: 0x prefixed hex string
    """
    priv = utils.sha3(private_key_seed_ascii)
    pub = bitcoin.encode_pubkey(bitcoin.privtopub(priv), 'bin_electrum')
    return "0x" + binascii.hexlify(sha3(pub)[12:]).decode("ascii")


def get_address_as_bytes(address: str) -> bytes:
    """Convert Ethereum address to byte data payload for signing."""
    assert address.startswith("0x")
    address_bytes = binascii.unhexlify(address[2:])
    return address_bytes


def sign(data: bytes, private_key_seed_ascii: str, hash_function=bitcoin.bin_sha256):
    """Sign data using Ethereum private key.

    :param private_key_seed_ascii: Private key seed as ASCII string
    """

    msghash = hash_function(data)

    priv = utils.sha3(private_key_seed_ascii)
    pub = bitcoin.privtopub(priv)

    # Based on ethereum/tesrt_contracts.py test_ecrecover
    pk = PrivateKey(priv, raw=True)

    signature = pk.ecdsa_recoverable_serialize(pk.ecdsa_sign_recoverable(msghash, raw=True))
    signature = signature[0] + utils.bytearray_to_bytestr([signature[1]])

    # Enforce non-tightly-packed arguments for signing
    # (0x00 left pad)
    # https://github.com/ethereum/web3.py/issues/466
    v = utils.safe_ord(signature[64]) + 27
    r_bytes = signature[0:32]
    r_bytes = pad_left(r_bytes, 32, b"\0")
    r = big_endian_to_int(r_bytes)
    s_bytes = signature[32:64]
    s_bytes = pad_left(s_bytes, 32, b"\0")
    s = big_endian_to_int(s_bytes)

    # Make sure we use bytes data and zero padding stays
    # good across different systems
    r_hex = binascii.hexlify(r_bytes).decode("ascii")
    s_hex = binascii.hexlify(s_bytes).decode("ascii")

    # Convert to Etheruem address format
    addr = utils.big_endian_to_int(utils.sha3(bitcoin.encode_pubkey(pub, 'bin')[1:])[12:])

    # Return various bits about signing so it's easier to debug
    return {
        "signature": signature,
        "v": v,
        "r": r,
        "s": s,
        "r_bytes": r_bytes,
        "s_bytes": s_bytes,
        "r_hex": "0x" + r_hex,
        "s_hex": "0x" + s_hex,
        "address_bitcoin": addr,
        "address_ethereum": get_ethereum_address_from_private_key(priv),
        "public_key": pub,
        "hash": msghash,
        "payload": binascii.hexlify(bytes([v] + list(r_bytes)+ list(s_bytes,)))
    }


def verify(msghash: bytes, signature, public_key):
    """Verify that data has been signed with Etheruem private key.
    :param signature:
    :return:
    """

    V = utils.safe_ord(signature[64]) + 27
    R = big_endian_to_int(signature[0:32])
    S = big_endian_to_int(signature[32:64])

    return bitcoin.ecdsa_raw_verify(msghash, (V, R, S), public_key)

