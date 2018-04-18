"""ERC-20 compatibility."""
import pytest
from web3.contract import Contract
from rlp.utils import decode_hex

@pytest.fixture
def testpayload() -> str:
    return decode_hex("a3e76c0f") # function receive() returns(bool)

@pytest.fixture
def receiver(chain, team_multisig, token_name, token_symbol, initial_supply) -> Contract:
    """Create the token contract."""

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('ERC827Receiver', deploy_transaction=tx)
    return contract

def test_erc827_allowance(token, team_multisig, testpayload, receiver, customer):
    """Token satisfies ERC-827 interface."""

    assert token.call().allowance(team_multisig, customer) == 0
    token.transact({"from": team_multisig}).approve(customer, 50, testpayload)
    assert token.call().allowance(team_multisig, customer) == 50
    token.transact({"from": team_multisig}).increaseApproval(customer, 100, testpayload)
    assert token.call().allowance(team_multisig, customer) == 150
    token.transact({"from": team_multisig}).decreaseApproval(customer, 50, testpayload)
    assert token.call().allowance(team_multisig, customer) == 100

    token.transact({"from": customer}).transferFrom(team_multisig, receiver.address, 100, testpayload)

def test_erc827_transfer(token, team_multisig, testpayload, receiver):
    assert token.call().balanceOf(receiver.address) == 0
    token.transact({"from": team_multisig}).transfer(receiver.address, 100, testpayload)
    assert token.call().balanceOf(receiver.address) == 100
