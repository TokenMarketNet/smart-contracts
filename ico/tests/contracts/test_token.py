"""Token core functionality."""

import pytest
from ethereum.tester import TransactionFailed
from web3.contract import Contract

@pytest.fixture
def token_new_name() -> str:
    return "New name"

@pytest.fixture
def token_new_symbol() -> str:
    return "NEW"

def test_token_initialized(token: Contract, team_multisig: str, token_symbol: str, token_name: str, initial_supply: int):
    """Token is initialized with the parameters we want."""
    assert token.call().owner() == team_multisig
    assert token.call().symbol() == token_symbol
    assert token.call().name() == token_name
    assert token.call().totalSupply() == initial_supply


def test_malicious_transfer_agent_set(token: Contract, malicious_address):
    """Externals cannot whitelist transfer agents."""

    with pytest.raises(TransactionFailed):
        token.transact({"from": malicious_address}).setTransferAgent(malicious_address, True)

def test_token_rename(token: Contract, team_multisig, token_new_name, token_new_symbol):
    """We will update token's information here"""

    token.transact({"from": team_multisig}).setTokenInformation(token_new_name, token_new_symbol)

    assert token.call().name() == token_new_name
    assert token.call().symbol() == token_new_symbol
