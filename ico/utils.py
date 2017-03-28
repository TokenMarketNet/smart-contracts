from web3 import Web3
from web3.contract import Contract
from web3.utils.abi import get_constructor_abi
from web3.utils.transactions import wait_for_transaction_receipt


def check_succesful_tx(web3: Web3, txid: str, timeout=180) -> dict:
    """See if transaction went through (Solidity code did not throw).

    :return: Transaction receipt
    """

    # http://ethereum.stackexchange.com/q/6007/620
    receipt = wait_for_transaction_receipt(web3, txid, timeout=timeout)
    txinfo = web3.eth.getTransaction(txid)

    # EVM has only one error mode and it's consume all gas
    assert txinfo["gas"] != receipt["gasUsed"]
    return receipt


def get_constructor_arguments(contract: Contract, args: list):
    """Get constructor arguments for Etherscan verify.

    https://etherscanio.freshdesk.com/support/solutions/articles/16000053599-contract-verification-constructor-arguments
    """
    constructor_abi = get_constructor_abi(contract.abi)
    return contract._encode_abi(constructor_abi, args)[2:]  # No 0x
