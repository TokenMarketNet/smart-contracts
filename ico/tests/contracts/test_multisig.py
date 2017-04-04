"""Multisig wallet tests.

"""
import pytest
from eth_utils import to_wei
from web3 import Web3

from populus.chain import TestRPCChain
from web3.contract import Contract


@pytest.fixture
def cosigner(accounts):
    return accounts[1]


@pytest.fixture
def cosigner_2(accounts):
    return accounts[2]


@pytest.fixture
def cosigner_3(accounts):
    return accounts[3]


@pytest.fixture
def dest_addr(accounts):
    return accounts[4]


@pytest.fixture
def source_addr(accounts):
    return accounts[5]


@pytest.fixture
def multisig(chain, cosigner, cosigner_2, cosigner_3) -> Contract:
    """Deploy a multisig wallet without a daily limit."""

    args = [
        [cosigner_2, cosigner_3],
        2, # 2/3 out of 3
        0,
    ]

    tx = {
        "from": cosigner,
    }

    wallet, hash = chain.provider.deploy_contract('Wallet', deploy_args=args, deploy_transaction=tx)
    return wallet


def test_cosign(chain: TestRPCChain, web3: Web3, multisig, cosigner, cosigner_2, cosigner_3, source_addr, dest_addr):
    """Move money through multisig wallet."""

    # No balance at the start
    assert web3.eth.getBalance(multisig.address) == 0

    source_balance = web3.eth.getBalance(source_addr)
    value = to_wei("1", "ether")

    # Move money to multisig
    web3.eth.sendTransaction({"from": source_addr, "to": multisig.address, "value": value})
    assert web3.eth.getBalance(multisig.address) == value
    assert web3.eth.getBalance(source_addr) - source_balance < value  # TX out

    # Move money out of multisig
    value_2 = to_wei("0.9", "ether")
    dest_balance = web3.eth.getBalance(dest_addr)
    multisig.transact({"from": cosigner}).execute(dest_addr, value_2, b"")

    # No balance change yet in the destination
    assert web3.eth.getBalance(dest_addr) == dest_balance

    # We have a confirmation hash
    events = multisig.pastEvents("Confirmation").get()
    assert len(events) == 1
    e = events[-1]
    assert e["args"]["owner"] == cosigner
    operation_id = e["args"]["operation"]

    # Confirm by cosigner 2
    multisig.transact({"from": cosigner_2}).confirm(operation_id)

    # We got a transaction
    events = multisig.pastEvents("MultiTransact").get()
    assert len(events) == 1
    e = events[-1]
    assert e["args"]["to"] == dest_addr
    assert e["args"]["value"] == value_2
    assert e["args"]["data"] == ""

    # ETH moved out
    assert web3.eth.getBalance(dest_addr) > dest_balance

