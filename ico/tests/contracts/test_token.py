"""Token core functionality."""

import datetime
import pytest
from ethereum.tester import TransactionFailed
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
    assert contract.call().balanceOf(team_multisig) == 1000000

    contract.transact({"from": team_multisig}).releaseTokenTransfer()
    return contract


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


def test_own_token_recovery(token: Contract, team_multisig, release_agent):
    """Let's try to recover other tokens from the contract"""
    original_balance = token.call().balanceOf(team_multisig)

    token.transact({"from": team_multisig}).setReleaseAgent(release_agent.address)
    release_agent.transact({"from": team_multisig}).release()

    token.transact({"from": team_multisig}).transfer(token.address, 1)
    assert token.call().balanceOf(team_multisig) != original_balance

    token.transact({"from": team_multisig}).recoverTokens(token.address)

    assert token.call().balanceOf(team_multisig) == original_balance


def test_other_token_recovery_only_owner(token: Contract, other_token: Contract, team_multisig, release_agent, malicious_address):
    """Only the owner can recover ERC-20 tokens."""

    token.transact({"from": team_multisig}).setReleaseAgent(release_agent.address)
    release_agent.transact({"from": team_multisig}).release()

    other_token.transact({"from": team_multisig}).transfer(token.address, 1)

    with pytest.raises(TransactionFailed):
        token.transact({"from": malicious_address}).recoverTokens(other_token.address)


