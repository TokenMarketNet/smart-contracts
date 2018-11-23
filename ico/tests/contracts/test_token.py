"""Token core functionality."""

import datetime
import pytest
from eth_tester.exceptions import TransactionFailed
from web3.contract import Contract

@pytest.fixture
def token_new_name() -> str:
    return "New name"


@pytest.fixture
def token_new_symbol() -> str:
    return "NEW"


@pytest.fixture
def other_token(chain, team_multisig):
    args = [
        team_multisig,
        "OtherToken",
        "OTH",
        1000000,
        0,
        int((datetime.datetime(2017, 4, 22, 16, 0) - datetime.datetime(1970, 1, 1)).total_seconds())
    ]
    contract, hash = chain.provider.deploy_contract('CentrallyIssuedToken', deploy_args=args)
    assert contract.functions.balanceOf(team_multisig).call() == 1000000

    contract.functions.releaseTokenTransfer().transact({"from": team_multisig})
    return contract


def test_token_initialized(token: Contract, team_multisig: str, token_symbol: str, token_name: str, initial_supply: int):
    """Token is initialized with the parameters we want."""
    assert token.functions.owner().call() == team_multisig
    assert token.functions.symbol().call() == token_symbol
    assert token.functions.name().call() == token_name
    assert token.functions.totalSupply().call() == initial_supply


def test_malicious_transfer_agent_set(token: Contract, malicious_address):
    """Externals cannot whitelist transfer agents."""

    with pytest.raises(TransactionFailed):
        token.functions.setTransferAgent(malicious_address, True).transact({"from": malicious_address})


def test_token_rename(token: Contract, team_multisig, token_new_name, token_new_symbol):
    """We will update token's information here"""

    token.functions.setTokenInformation(token_new_name, token_new_symbol).transact({"from": team_multisig})

    assert token.functions.name().call() == token_new_name
    assert token.functions.symbol().call() == token_new_symbol


def test_own_token_recovery(token: Contract, team_multisig, release_agent):
    """Let's try to recover other tokens from the contract"""
    original_balance = token.functions.balanceOf(team_multisig).call()

    token.functions.setReleaseAgent(release_agent.address).transact({"from": team_multisig})
    release_agent.functions.release().transact({"from": team_multisig})

    token.functions.transfer(token.address, 1).transact({"from": team_multisig})
    assert token.functions.balanceOf(team_multisig).call() != original_balance

    token.functions.recoverTokens(token.address).transact({"from": team_multisig})

    assert token.functions.balanceOf(team_multisig).call() == original_balance


def test_other_token_recovery_only_owner(token: Contract, other_token: Contract, team_multisig, release_agent, malicious_address):
    """Only the owner can recover ERC-20 tokens."""

    token.functions.setReleaseAgent(release_agent.address).transact({"from": team_multisig})
    release_agent.functions.release().transact({"from": team_multisig})

    other_token.functions.transfer(token.address, 1).transact({"from": team_multisig})

    with pytest.raises(TransactionFailed):
        token.functions.recoverTokens(other_token.address).transact({"from": malicious_address})


