from typing import Optional

from decimal import Decimal

import web3
from eth_utils import add_0x_prefix
from ethereum.chain import Chain
from populus.utils.contracts import CONTRACT_FACTORY_FIELDS
from web3 import Web3
from web3.contract import Contract
from web3.utils.abi import get_constructor_abi, merge_args_and_kwargs
from web3.utils.transactions import wait_for_transaction_receipt

from populus.chain.base import BaseChain
from populus.contracts.contract import build_populus_meta, PopulusContract

truthy = frozenset(('t', 'true', 'y', 'yes', 'on', '1'))
falsey = frozenset(('f', 'false', 'n', 'no', 'off', '0'))


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


def check_succesful_tx(web3: Web3, txid: str, timeout=180) -> dict:
    """See if transaction went through (Solidity code did not throw).

    :return: Transaction receipt
    """

    # http://ethereum.stackexchange.com/q/6007/620
    receipt = wait_for_transaction_receipt(web3, txid, timeout=timeout)
    txinfo = web3.eth.getTransaction(txid)

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
    constructor_abi = get_constructor_abi(contract.abi)

    if args is not None:
        return contract._encode_abi(constructor_abi, args)[2:]  # No 0x
    else:
        constructor_abi = get_constructor_abi(contract.abi)
        arguments = merge_args_and_kwargs(constructor_abi, [], kwargs)
        deploy_data = add_0x_prefix(
            contract._encode_abi(constructor_abi, arguments)
        )
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

    factory_kwargs = {
        key: contract_data[key]
        for key
        in CONTRACT_FACTORY_FIELDS
        if key in contract_data
    }

    populus_meta = build_populus_meta(chain, contract_data)
    Contract = chain.web3.eth.contract(
        ContractFactoryClass=PopulusContract,
        populus_meta=populus_meta,
        **factory_kwargs,
    )

    return Contract


