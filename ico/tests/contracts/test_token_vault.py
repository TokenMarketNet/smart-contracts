"""Token core functionality."""

import datetime
import enum
import pytest
from ethereum.tester import TransactionFailed
from ico.tests.utils import time_travel
from web3.contract import Contract


class TokenVaultState(enum.IntEnum):
    Unknown = 0
    Loading = 1
    Holding = 2
    Distributing = 3


@pytest.fixture
def token(chain, team_multisig):
    args = [
        team_multisig,
        "Token",
        "TKN",
        1000000,
        0,
        int((datetime.datetime(2017, 4, 22, 16, 0) - datetime.datetime(1970, 1, 1)).total_seconds())
    ]
    contract, hash = chain.provider.deploy_contract('CentrallyIssuedToken', deploy_args=args)
    assert contract.call().balanceOf(team_multisig) == 1000000

    contract.transact({"from": team_multisig}).releaseTokenTransfer()
    return contract


@pytest.fixture
def freeze_ends_at(chain) -> int:
    return 1970 + 60*365*24*3600


@pytest.fixture
def token_vault_balances(chain, customer, customer_2) -> list:
    return [
       (customer, 1000),
       (customer_2, 2000),
    ]


@pytest.fixture
def token_vault(chain, team_multisig, token, freeze_ends_at, token_vault_balances) -> Contract:
    """A test fixture to deploy a token vault."""

    total = 1000 + 2000

    args = [
        team_multisig,
        freeze_ends_at,
        token.address,
        total,
    ]
    contract, hash = chain.provider.deploy_contract('TokenVault', deploy_args=args)
    return contract


@pytest.fixture
def token_vault_single(chain, team_multisig, token, freeze_ends_at, token_vault_balances) -> Contract:
    """Another token vault deployment with a single customer."""

    total = 1000

    args = [
        team_multisig,
        freeze_ends_at,
        token.address,
        total,
    ]
    contract, hash = chain.provider.deploy_contract('TokenVault', deploy_args=args)
    return contract


@pytest.fixture
def loaded_token_vault(token_vault, team_multisig, token_vault_balances):
    """Token vault with investor balances set."""
    for address, balance in token_vault_balances:
        token_vault.transact({"from": team_multisig}).setInvestor(address, balance)
    return token_vault


@pytest.fixture
def distributing_token_vault(chain, loaded_token_vault, team_multisig, token, token_vault_balances):
    """Token vault set to distributing state."""

    token.transact({"from": team_multisig}).transfer(loaded_token_vault.address, 3000)
    loaded_token_vault.transact({"from": team_multisig}).lock()

    assert loaded_token_vault.call().getState() == TokenVaultState.Holding
    time_travel(chain, loaded_token_vault.call().freezeEndsAt()+1)
    loaded_token_vault.call().getState() == TokenVaultState.Distributing

    return loaded_token_vault


def test_load_vault(loaded_token_vault, team_multisig, token, customer, customer_2):
    """We load data correctly."""
    assert loaded_token_vault.call().getState() == TokenVaultState.Loading
    assert loaded_token_vault.call().balances(customer) == 1000
    assert loaded_token_vault.call().balances(customer_2) == 2000
    assert loaded_token_vault.call().investorCount() == 2
    assert loaded_token_vault.call().tokensAllocatedTotal() == 3000


def test_load_vault_not_owner(token_vault, team_multisig, token, malicious_address, token_vault_balances):
    """Unknown party cannot set investors.."""

    for address, balance in token_vault_balances:
        with pytest.raises(TransactionFailed):
            token_vault.transact({"from": malicious_address}).setInvestor(address, balance)


def test_load_vault_twice(loaded_token_vault, team_multisig, token, token_vault_balances):
    """We cannot reset investor data."""

    for address, balance in token_vault_balances:
        with pytest.raises(TransactionFailed):
            loaded_token_vault.transact({"from": team_multisig}).setInvestor(address, balance)


def test_lock(loaded_token_vault, team_multisig, token, customer, customer_2):
    """We can lock with correct data."""
    assert loaded_token_vault.call().getState() == TokenVaultState.Loading

    # Move in tokens
    token.transact({"from" : team_multisig}).transfer(loaded_token_vault.address, 3000)

    # All balances are correct
    assert token.call().balanceOf(loaded_token_vault.address) == 3000
    assert loaded_token_vault.call().tokensAllocatedTotal() == 3000
    assert loaded_token_vault.call().tokensToBeAllocated() == 3000

    loaded_token_vault.transact({"from": team_multisig}).lock()

    assert loaded_token_vault.call().getState() == TokenVaultState.Holding

def test_recover(loaded_token_vault, team_multisig, token, customer, customer_2):
    """Can we recover tokens which are sent after locking?"""
    assert loaded_token_vault.call().getState() == TokenVaultState.Loading

    # Move in tokens
    token.transact({"from" : team_multisig}).transfer(loaded_token_vault.address, 3000)

    # All balances are correct
    assert token.call().balanceOf(loaded_token_vault.address) == 3000
    assert loaded_token_vault.call().tokensAllocatedTotal() == 3000
    assert loaded_token_vault.call().tokensToBeAllocated() == 3000

    loaded_token_vault.transact({"from": team_multisig}).lock()

    assert loaded_token_vault.call().getState() == TokenVaultState.Holding
    assert loaded_token_vault.call().tokensToBeReturned(token.address) == 0

    token.transact({"from" : team_multisig}).transfer(loaded_token_vault.address, 1000)
    assert token.call().balanceOf(loaded_token_vault.address) == 4000
    loaded_token_vault.transact({"from" : team_multisig}).recoverTokens(token.address)
    assert token.call().balanceOf(loaded_token_vault.address) == 3000

def test_lock_incorrectly(loaded_token_vault, team_multisig, token, customer, customer_2):
    """In the case of lock fails, we can redeem the tokens.."""
    assert loaded_token_vault.call().getState() == TokenVaultState.Loading

    # Move wrong amount tokens
    token.transact({"from": team_multisig}).transfer(loaded_token_vault.address, 4000)

    assert loaded_token_vault.call().getState() == TokenVaultState.Loading

    # Failed lock attempt
    with pytest.raises(TransactionFailed):
        loaded_token_vault.transact({"from": team_multisig}).lock()

    assert loaded_token_vault.call().getState() == TokenVaultState.Loading

    # Move tokens to back to the owner
    before_balance =token.call().balanceOf(team_multisig)
    loaded_token_vault.transact({"from": team_multisig}).recoverFailedLock()
    after_balance = token.call().balanceOf(team_multisig)

    assert after_balance - before_balance == 4000


def test_load_after_lock(token_vault_single, team_multisig, token, customer, customer_2):
    """After locking, no new invetors can be added."""

    token_vault = token_vault_single

    assert token_vault.call().getState() == TokenVaultState.Loading

    token_vault.transact({"from": team_multisig}).setInvestor(customer, 1000)

    # Move in tokens and lock
    token.transact({"from": team_multisig}).transfer(token_vault.address, 1000)
    token_vault.transact({"from": team_multisig}).lock()
    assert token_vault.call().getState() == TokenVaultState.Holding

    with pytest.raises(TransactionFailed):
        token_vault.transact({"from": team_multisig}).setInvestor(customer_2, 2000)


def test_claim(distributing_token_vault, team_multisig, token, customer, customer_2):
    """Tokens can be claimed after freeze time is over."""

    assert token.call().balanceOf(customer) == 0
    distributing_token_vault.transact({"from": customer}).claim()
    assert token.call().balanceOf(customer) == 1000
    assert distributing_token_vault.call().balances(customer) == 1000
    assert distributing_token_vault.call().claimed(customer) == 1000

    assert token.call().balanceOf(customer_2) == 0
    distributing_token_vault.transact({"from": customer_2}).claim()
    assert token.call().balanceOf(customer_2) == 2000

    assert distributing_token_vault.call().totalClaimed() == 3000


def test_claim_twice(distributing_token_vault, team_multisig, token, customer, customer_2):
    """Investor cannot make claim twice."""

    distributing_token_vault.transact({"from": customer}).claim()
    with pytest.raises(TransactionFailed):
        distributing_token_vault.transact({"from": customer}).claim()


def test_claim_unknown(distributing_token_vault, team_multisig, malicious_address):
    """Third parties cannot make a claim."""

    with pytest.raises(TransactionFailed):
        distributing_token_vault.transact({"from": malicious_address}).claim()


def test_claim_early(chain, loaded_token_vault, team_multisig, token, customer, customer_2):
    """Tokens cannot be claimed early."""

    token.transact({"from": team_multisig}).transfer(loaded_token_vault.address, 3000)
    loaded_token_vault.transact({"from": team_multisig}).lock()

    time_travel(chain, loaded_token_vault.call().freezeEndsAt() - 1)

    with pytest.raises(TransactionFailed):
        loaded_token_vault.transact({"from": customer}).claim()
