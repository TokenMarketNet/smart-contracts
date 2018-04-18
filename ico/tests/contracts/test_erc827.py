"""ERC-20 compatibility."""
import pytest
from web3.contract import Contract
from ethereum.tester import TransactionFailed
from rlp.utils import decode_hex

@pytest.fixture
def testpayload() -> str:
    return decode_hex("a3e76c0f") # function receive() returns(bool)

@pytest.fixture
def receiver(chain, team_multisig, token_name, token_symbol, initial_supply) -> Contract:
    """Create the receiver contract for callback testing."""

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('ERC827Receiver', deploy_transaction=tx)
    return contract

def test_erc827_allowance(token, team_multisig, testpayload, receiver, customer):
    """Testing succesful approve+transferFrom combination"""

    assert token.call().allowance(team_multisig, customer) == 0
    token.transact({"from": team_multisig}).approve(customer, 50, testpayload)
    assert token.call().allowance(team_multisig, customer) == 50
    token.transact({"from": team_multisig}).increaseApproval(customer, 100, testpayload)
    assert token.call().allowance(team_multisig, customer) == 150
    token.transact({"from": team_multisig}).decreaseApproval(customer, 50, testpayload)
    assert token.call().allowance(team_multisig, customer) == 100

    token.transact({"from": customer}).transferFrom(team_multisig, receiver.address, 100, testpayload)

def test_erc827_allowance_bad_amount(token, team_multisig, testpayload, receiver, customer):
    """Testing unsuccesful approve+transferFrom combination with too large amount"""

    assert token.call().allowance(team_multisig, customer) == 0
    token.transact({"from": team_multisig}).approve(customer, 50, testpayload)
    assert token.call().allowance(team_multisig, customer) == 50

    with pytest.raises(TransactionFailed):
        token.transact({"from": customer}).transferFrom(team_multisig, receiver.address, 100, testpayload)

def test_erc827_allowance_bad_claimant(token, team_multisig, testpayload, receiver, customer, customer_2):
    """Testing unsuccesful approve+transferFrom combination by 3rd party"""

    assert token.call().allowance(team_multisig, customer) == 0
    token.transact({"from": team_multisig}).approve(customer, 50, testpayload)
    assert token.call().allowance(team_multisig, customer) == 50

    with pytest.raises(TransactionFailed):
        token.transact({"from": customer_2}).transferFrom(team_multisig, receiver.address, 50, testpayload)

def test_erc827_allowance_without_approve(token, team_multisig, testpayload, receiver, customer, customer_2):
    """Testing succesful transferFrom without approve()"""

    assert token.call().allowance(team_multisig, customer) == 0

    with pytest.raises(TransactionFailed):
        token.transact({"from": customer}).transferFrom(team_multisig, receiver.address, 50, testpayload)

def test_erc827_transfer(token, team_multisig, testpayload, receiver):
    """Testing succesful token transfer"""
    assert token.call().balanceOf(receiver.address) == 0
    token.transact({"from": team_multisig}).transfer(receiver.address, 100, testpayload)
    assert token.call().balanceOf(receiver.address) == 100

def test_erc827_transfer_bad_amount(token, team_multisig, testpayload, receiver):
    """Testing unsuccesful token transfer with too large amount"""
    original_balance = token.call().balanceOf(team_multisig)

    assert token.call().balanceOf(receiver.address) == 0
    with pytest.raises(TransactionFailed):
        token.transact({"from": team_multisig}).transfer(receiver.address, 10000000000000000000000000000000000, testpayload)
    assert token.call().balanceOf(receiver.address) == 0
    assert token.call().balanceOf(team_multisig) == original_balance
