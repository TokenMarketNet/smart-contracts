from typing import Optional

from decimal import Decimal
from eth_abi import encode_abi
from eth_abi.exceptions import EncodingError
from eth_utils import add_0x_prefix
from eth_utils import encode_hex
from eth_utils import force_bytes
from eth_utils import force_obj_to_bytes
from eth_utils import remove_0x_prefix
from web3 import Web3
from web3.contract import Contract
from web3.utils.abi import get_constructor_abi, get_abi_input_types, check_if_arguments_can_be_encoded, merge_args_and_kwargs
from web3.utils.transactions import wait_for_transaction_receipt

from populus.chain.base import BaseChain
from populus.contracts.provider import Provider
from populus.utils.linking import find_link_references


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


def get_libraries(chain: BaseChain, contract_name, contract: Contract) -> dict:
    """Get libraries of a deployed contract.

    TODO: drop contract_name https://github.com/pipermerriam/web3.py/issues/172

    :return dict: Library name -> address pairs
    """

    unlinked = chain.provider.get_base_contract_factory(contract_name)
    refs = find_link_references(unlinked.bytecode, chain.provider.get_all_contract_names())

    def get_address(name):
        return chain.registrar.get_contract_addresses(name)[0]

    libraries = {
        contract_name: get_address(contract_name)
        for contract_name in set(ref.full_name for ref in refs)
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


