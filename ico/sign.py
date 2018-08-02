"""Sign data with Ethereum private key."""
import binascii
import hashlib

from eth_account import Account
from eth_keys import KeyAPI
from eth_keys.datatypes import PublicKey, PrivateKey, Signature
from eth_utils import to_bytes, keccak
from web3 import Web3


CHAIN_ID_OFFSET = 35
V_OFFSET = 27


def sha256_msg(msg: bytes) -> bytes:
    return to_bytes(hexstr=hashlib.sha256(msg).hexdigest())


def get_ethereum_address_from_private_key(private_key_seed_ascii: str) -> str:
    """Generate Ethereum address from a private key.

    :param private_key: Any string as a seed

    :return: 0x prefixed hex string
    """
    priv_key = Web3.sha3(text=private_key_seed_ascii)
    acc = Account.privateKeyToAccount(priv_key)
    return acc.address


def get_address_as_bytes(address: str) -> bytes:
    """Convert Ethereum address to byte data payload for signing."""
    assert address.startswith("0x")
    address_bytes = binascii.unhexlify(address[2:])
    return address_bytes


def to_eth_v(v_raw, chain_id=None):
    """
    Implementation of EIP 155
    """
    if chain_id is None:
        v = v_raw + V_OFFSET
    else:
        v = v_raw + CHAIN_ID_OFFSET + 2 * chain_id
    return v


def sign(data: bytes, private_key_seed_ascii: str, hash_function=sha256_msg):
    """Sign data using Ethereum private key.

    :param private_key_seed_ascii: Private key seed as ASCII string
    """
    priv_key = PrivateKey(Web3.sha3(text=private_key_seed_ascii))
    msghash = hash_function(data)
    signature = priv_key.sign_msg_hash(msghash)
    v, r, s = signature.vrs
    # assuming chainID is 1 i.e the main net
    # TODO: take in chainID as a param, so that v is set appropriately
    # currently there's no good way to determine chainID
    v = to_eth_v(v)
    r_bytes = to_bytes(r)
    s_bytes = to_bytes(s)

    # Make sure we use bytes data and zero padding stays
    # good across different systems
    r_hex = binascii.hexlify(r_bytes).decode("ascii")
    s_hex = binascii.hexlify(s_bytes).decode("ascii")

    # Convert to Etheruem address format
    pub_key = priv_key.public_key
    addr = pub_key.to_checksum_address()
    pub = pub_key.to_bytes()
    #
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
        "address_ethereum": get_ethereum_address_from_private_key(private_key_seed_ascii),
        "public_key": pub,
        "hash": msghash,
        "payload": binascii.hexlify(bytes([v] + list(r_bytes) + list(s_bytes,)))
    }


def verify(msghash: bytes, signature, public_key):
    """Verify that data has been signed with Etheruem private key.
    :param signature:
    :return:
    """
    key_api = KeyAPI('eth_keys.backends.NativeECCBackend')
    return key_api.ecdsa_verify(msghash, Signature(signature), PublicKey(public_key))
