from typing import Optional

from decimal import Decimal

import time
import web3
from eth_utils import is_hex_address, is_checksum_address, add_0x_prefix
from populus.utils.contracts import CONTRACT_FACTORY_FIELDS
from web3 import Web3
from web3.contract import Contract
from web3.utils.abi import get_constructor_abi, merge_args_and_kwargs
from web3.utils.contracts import encode_abi
from web3.utils.transactions import wait_for_transaction_receipt

from populus.chain.base import BaseChain
from populus.contracts.contract import build_populus_meta, PopulusContract

truthy = frozenset(('t', 'true', 'y', 'yes', 'on', '1'))
falsey = frozenset(('f', 'false', 'n', 'no', 'off', '0'))

CONTRACT_FIELDS_TO_REMOVE = {
    'bytecode',
    'bytecode_runtime',
}


class TransactionFailure(Exception):
    """We waited transaction to be mined and it did not happen.

    Usually throw statement in Solidity code or not enough gas.
    """


def asbool(s):
    """ Return the boolean value ``True`` if the case-lowered value of string
    input ``s`` is a :term:`truthy string`. If ``s`` is already one of the
    boolean values ``True`` or ``False``, return it."""
    if s is None:
        return False
    if isinstance(s, bool):
        return s
    s = str(s).strip()
    return s.lower() in truthy


def check_succesful_tx(web3: Web3, txid: str, timeout=600) -> dict:
    """See if transaction went through (Solidity code did not throw).

    :return: Transaction receipt
    """

    # http://ethereum.stackexchange.com/q/6007/620
    receipt = wait_for_transaction_receipt(web3, txid, timeout=timeout)
    txinfo = web3.eth.getTransaction(txid)
    if not txinfo:
        # This is some sort of geth flakiness issue, not sure what
        # Try to mitigate it with timeout
        time.sleep(1.0)
        txinfo = web3.eth.getTransaction(txid)

    if receipt is None:
        raise RuntimeError("Did not get receipt for {}".format(txid))

    if txinfo is None:
        raise RuntimeError("Did not get txinfo for {}".format(txid))

    # EVM has only one error mode and it's consume all gas
    if txinfo["gas"] == receipt["gasUsed"]:
        raise TransactionFailure("Transaction failed: {}".format(txid))
    return receipt


def check_multiple_succesful_txs(web3: Web3, tx_list: list, timeout=1800):
    """Check that multiple transactions confirmed"""
    for tx in tx_list:
        check_succesful_tx(web3, tx, timeout)


def get_constructor_arguments(contract: Contract, args: Optional[list]=None, kwargs: Optional[dict]=None):
    """Get constructor arguments for Etherscan verify.

    https://etherscanio.freshdesk.com/support/solutions/articles/16000053599-contract-verification-constructor-arguments
    """

    # return contract._encode_constructor_data(args=args, kwargs=kwargs)

    constructor_abi = get_constructor_abi(contract.abi)

    if args is not None:
        return contract._encode_abi(constructor_abi, args)[2:]  # No 0x
    else:
        constructor_abi = get_constructor_abi(contract.abi)
        kwargs = kwargs or {}
        arguments = merge_args_and_kwargs(constructor_abi, [], kwargs)
        # deploy_data = add_0x_prefix(
        #    contract._encode_abi(constructor_abi, arguments)
        #)

        # TODO: Looks like recent Web3.py ABI change
        deploy_data = encode_abi(contract.web3, constructor_abi, arguments)
        return deploy_data


def get_libraries(chain: BaseChain, contract_name: str, contract: Contract) -> dict:
    """Get library addresses of a deployed contract.

    * The contract must be deployed

    * Chain stores linkrefs for deployed contracts

    * Look the addresses of already deployed library contracts from the chain by name

    TODO: Rewrite deployment and linking logic so that libraries are correctly shared across the contracts

    :param name: Name of a (just) deployed contract

    :return dict: Library name -> address pairs
    """

    contract_data = chain.provider.get_contract_data(contract_name)

    # link_refs looks like:
    # [{'name': 'SafeMathLib', 'length': 40, 'source_path': 'contracts/SafeMathLib.sol', 'start': 3304}]
    link_refs = contract_data["linkrefs"]

    def get_address(name):
        return chain.registrar.get_contract_addresses(name)[0]

    libraries = {
        contract_name: get_address(contract_name)
        for contract_name in set(ref["name"] for ref in link_refs)
    }
    return libraries


def decimalize_token_amount(contract: Contract, amount: int) -> Decimal:
    """Convert raw fixed point token amount to decimal format.

    :param contract: ERC-20 token contract with decimals field
    :param amount: Raw token amount
    :return: The resultdroping :py:class:`decimal.Decimal` carries a correct decimal places.
    """
    val = Decimal(amount) / Decimal(10 ** contract.call().decimals())
    quantizer = Decimal(1) /  Decimal(10 ** contract.call().decimals())
    return val.quantize(quantizer)


def get_contract_by_name(chain: BaseChain, name: str) -> web3.contract.Contract:
    """Get web3.Contract class by its name.

    Sanity wrapper over everchanging Populus ABI.
    """

    contract_data = chain.provider.get_contract_data(name)

    # There's a bug in populus where bytecode and bytecode-runtime can't be linked.
    # These fields are not needed during interaction with a smart contract,
    # so they can be ignored
    contract_factory_fields = filter(
        lambda x: x not in CONTRACT_FIELDS_TO_REMOVE,
        CONTRACT_FACTORY_FIELDS
    )

    factory_kwargs = {
        key: contract_data[key]
        for key
        in contract_factory_fields
        if key in contract_data
    }

    populus_meta = build_populus_meta(chain, contract_data)
    Contract = chain.web3.eth.contract(
        ContractFactoryClass=PopulusContract,
        populus_meta=populus_meta,
        **factory_kwargs,
    )

    return Contract


def validate_ethereum_address(address: str):
    """Clever Ethereum address validator."""

    if len(address) < 42:
        raise ValueError("Not an Ethereum address: {}".format(address))

    try:
        if not is_hex_address(address):
            raise ValueError("Not an Ethereum address: {}".format(address))
    except UnicodeEncodeError:
        raise ValueError("Could not decode: {}".format(address))

    # Check if checksummed address if any of the letters is upper case
    if any([c.isupper() for c in address]):
        if not is_checksum_address(address):
            raise ValueError("Not a checksummed Ethereum address: {}".format(address))
