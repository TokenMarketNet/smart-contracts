"""Token core functionality."""

import enum
import pytest
from eth_tester.exceptions import TransactionFailed
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
        chain.web3.eth.getBlock('pending').timestamp
    ]
    contract, hash = chain.provider.deploy_contract('CentrallyIssuedToken', deploy_args=args)
    assert contract.functions.balanceOf(team_multisig).call() == 1000000

    contract.functions.releaseTokenTransfer().transact({"from": team_multisig})
    return contract


@pytest.fixture
def other_token(chain, team_multisig):
    args = [
        team_multisig,
        "OtherToken",
        "OTH",
        1000000,
        0,
        chain.web3.eth.getBlock('pending').timestamp
    ]
    contract, hash = chain.provider.deploy_contract('CentrallyIssuedToken', deploy_args=args)
    assert contract.functions.balanceOf(team_multisig).call() == 1000000

    contract.functions.releaseTokenTransfer().transact({"from": team_multisig})
    return contract


@pytest.fixture
def freeze_ends_at(chain) -> int:
    return chain.web3.eth.getBlock('pending').timestamp + 60 * 365 * 24 * 3600


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
def token_vault_tapped(chain, team_multisig, token, freeze_ends_at) -> Contract:
    """Another token vault deployment with a single customer."""

    total = 3000

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
        token_vault.functions.setInvestor(address, balance, 0).transact({"from": team_multisig})
    return token_vault


@pytest.fixture
def distributing_token_vault(chain, loaded_token_vault, team_multisig, token, token_vault_balances):
    """Token vault set to distributing state."""

    token.functions.transfer(loaded_token_vault.address, 3000).transact({"from": team_multisig})
    loaded_token_vault.functions.lock().transact({"from": team_multisig})

    assert loaded_token_vault.functions.getState().call() == TokenVaultState.Holding
    time_travel(chain, loaded_token_vault.functions.freezeEndsAt().call()+1)
    assert loaded_token_vault.functions.getState().call() == TokenVaultState.Distributing

    return loaded_token_vault


def test_load_vault(loaded_token_vault, team_multisig, token, customer, customer_2):
    """We load data correctly."""
    assert loaded_token_vault.functions.getState().call() == TokenVaultState.Loading
    assert loaded_token_vault.functions.balances(customer).call() == 1000
    assert loaded_token_vault.functions.balances(customer_2).call() == 2000
    assert loaded_token_vault.functions.investorCount().call() == 2
    assert loaded_token_vault.functions.tokensAllocatedTotal().call() == 3000


def test_load_vault_not_owner(token_vault, team_multisig, token, malicious_address, token_vault_balances):
    """Unknown party cannot set investors.."""

    for address, balance in token_vault_balances:
        with pytest.raises(TransactionFailed):
            token_vault.functions.setInvestor(address, balance, 0).transact({"from": malicious_address})


def test_load_vault_twice(loaded_token_vault, team_multisig, token, token_vault_balances):
    """We cannot reset investor data."""

    for address, balance in token_vault_balances:
        with pytest.raises(TransactionFailed):
            loaded_token_vault.functions.setInvestor(address, balance, 0).transact({"from": team_multisig})


def test_lock(loaded_token_vault, team_multisig, token, customer, customer_2):
    """We can lock with correct data."""
    assert loaded_token_vault.functions.getState().call() == TokenVaultState.Loading

    # Move in tokens
    token.functions.transfer(loaded_token_vault.address, 3000).transact({"from" : team_multisig})

    # All balances are correct
    assert token.functions.balanceOf(loaded_token_vault.address).call() == 3000
    assert loaded_token_vault.functions.tokensAllocatedTotal().call() == 3000
    assert loaded_token_vault.functions.tokensToBeAllocated().call() == 3000

    loaded_token_vault.functions.lock().transact({"from": team_multisig})

    assert loaded_token_vault.functions.getState().call() == TokenVaultState.Holding

def test_recover(loaded_token_vault, team_multisig, token, customer, customer_2):
    """Can we recover tokens which are sent after locking?"""
    assert loaded_token_vault.functions.getState().call() == TokenVaultState.Loading

    # Move in tokens
    token.functions.transfer(loaded_token_vault.address, 3000).transact({"from" : team_multisig})

    # All balances are correct
    assert token.functions.balanceOf(loaded_token_vault.address).call() == 3000
    assert loaded_token_vault.functions.tokensAllocatedTotal().call() == 3000
    assert loaded_token_vault.functions.tokensToBeAllocated().call() == 3000

    loaded_token_vault.functions.lock().transact({"from": team_multisig})

    assert loaded_token_vault.functions.getState().call() == TokenVaultState.Holding
    assert loaded_token_vault.functions.tokensToBeReturned(token.address).call() == 0

    token.functions.transfer(loaded_token_vault.address, 1000).transact({"from" : team_multisig})
    assert token.functions.balanceOf(loaded_token_vault.address).call() == 4000
    loaded_token_vault.functions.recoverTokens(token.address).transact({"from" : team_multisig})
    assert token.functions.balanceOf(loaded_token_vault.address).call() == 3000

def test_lock_incorrectly(loaded_token_vault, team_multisig, token, customer, customer_2):
    """In the case of lock fails, we can redeem the tokens.."""
    assert loaded_token_vault.functions.getState().call() == TokenVaultState.Loading

    # Move wrong amount tokens
    token.functions.transfer(loaded_token_vault.address, 4000).transact({"from": team_multisig})

    assert loaded_token_vault.functions.getState().call() == TokenVaultState.Loading

    # Failed lock attempt
    with pytest.raises(TransactionFailed):
        loaded_token_vault.functions.lock().transact({"from": team_multisig})

    assert loaded_token_vault.functions.getState().call() == TokenVaultState.Loading

    # Move tokens to back to the owner
    before_balance =token.functions.balanceOf(team_multisig).call()
    loaded_token_vault.functions.recoverFailedLock().transact({"from": team_multisig})
    after_balance = token.functions.balanceOf(team_multisig).call()

    assert after_balance - before_balance == 4000


def test_load_after_lock(token_vault_single, team_multisig, token, customer, customer_2):
    """After locking, no new invetors can be added."""

    token_vault = token_vault_single

    assert token_vault.functions.getState().call() == TokenVaultState.Loading

    token_vault.functions.setInvestor(customer, 1000, 0).transact({"from": team_multisig})

    # Move in tokens and lock
    token.functions.transfer(token_vault.address, 1000).transact({"from": team_multisig})
    token_vault.functions.lock().transact({"from": team_multisig})
    assert token_vault.functions.getState().call() == TokenVaultState.Holding

    with pytest.raises(TransactionFailed):
        token_vault.functions.setInvestor(customer_2, 2000, 0).transact({"from": team_multisig})


def test_claim(distributing_token_vault, team_multisig, token, customer, customer_2):
    """Tokens can be claimed after freeze time is over."""

    assert token.functions.balanceOf(customer).call() == 0
    distributing_token_vault.functions.claim().transact({"from": customer})
    assert token.functions.balanceOf(customer).call() == 1000
    assert distributing_token_vault.functions.balances(customer).call() == 1000
    assert distributing_token_vault.functions.claimed(customer).call() == 1000

    assert token.functions.balanceOf(customer_2).call() == 0
    distributing_token_vault.functions.claim().transact({"from": customer_2})
    assert token.functions.balanceOf(customer_2).call() == 2000

    assert distributing_token_vault.functions.totalClaimed().call() == 3000


def test_claim_twice(distributing_token_vault, team_multisig, token, customer, customer_2):
    """Investor cannot make claim twice."""

    distributing_token_vault.functions.claim().transact({"from": customer})
    with pytest.raises(TransactionFailed):
        distributing_token_vault.functions.claim().transact({"from": customer})


def test_claim_unknown(distributing_token_vault, team_multisig, malicious_address):
    """Third parties cannot make a claim."""

    with pytest.raises(TransactionFailed):
        distributing_token_vault.functions.claim().transact({"from": malicious_address})


def test_claim_early(chain, loaded_token_vault, team_multisig, token, customer, customer_2):
    """Tokens cannot be claimed early."""

    token.functions.transfer(loaded_token_vault.address, 3000).transact({"from": team_multisig})
    loaded_token_vault.functions.lock().transact({"from": team_multisig})

    # two minutes before freeze
    time_travel(chain, loaded_token_vault.functions.freezeEndsAt().call() - 120)

    with pytest.raises(TransactionFailed):
        loaded_token_vault.functions.claim().transact({"from": customer})


def test_emergency_claim_our_token(chain, loaded_token_vault, team_multisig, token, customer, customer_2):
    """Trying to claim extra tokens we have sent."""

    token.functions.transfer(loaded_token_vault.address, 3000).transact({"from": team_multisig})
    loaded_token_vault.functions.lock().transact({"from": team_multisig})

    amount_after_locking = token.functions.balanceOf(team_multisig).call()
    token.functions.transfer(loaded_token_vault.address, 1).transact({"from": team_multisig})
    assert token.functions.balanceOf(team_multisig).call() != amount_after_locking

    loaded_token_vault.functions.recoverTokens(token.address).transact({"from": team_multisig})
    assert token.functions.balanceOf(team_multisig).call() == amount_after_locking


def test_emergency_claim_other_token(chain, loaded_token_vault, team_multisig, token, other_token, customer, customer_2):
    """Trying to claim extra tokens (other than the vault's own) we have sent."""

    token.functions.transfer(loaded_token_vault.address, 3000).transact({"from": team_multisig})
    loaded_token_vault.functions.lock().transact({"from": team_multisig})

    amount_after_locking = other_token.functions.balanceOf(team_multisig).call()
    other_token.functions.transfer(loaded_token_vault.address, 1).transact({"from": team_multisig})
    assert other_token.functions.balanceOf(team_multisig).call() != amount_after_locking

    loaded_token_vault.functions.recoverTokens(other_token.address).transact({"from": team_multisig})
    assert other_token.functions.balanceOf(team_multisig).call() == amount_after_locking


def test_tapped_claim(chain, token_vault_tapped, team_multisig, token, customer, customer_2, token_vault_balances):
    """Tokens can be claimed after freeze time is over."""
    for address, balance in token_vault_balances:
        token_vault_tapped.functions.setInvestor(address, balance, 1).transact({"from": team_multisig})

    token.functions.transfer(token_vault_tapped.address, 3000).transact({"from": team_multisig})
    token_vault_tapped.functions.lock().transact({"from": team_multisig})

    assert token_vault_tapped.functions.getState().call() == TokenVaultState.Holding

    time_travel(chain, token_vault_tapped.functions.freezeEndsAt().call() + 2 - 1)
    assert token_vault_tapped.functions.getState().call() == TokenVaultState.Distributing

    assert token.functions.balanceOf(customer).call() == 0
    token_vault_tapped.functions.claim().transact({"from": customer})
    assert token.functions.balanceOf(customer).call() == 2
    assert token_vault_tapped.functions.balances(customer).call() == 1000


    time_travel(chain, token_vault_tapped.call().freezeEndsAt() + 400 - 1)
    token_vault_tapped.functions.claim().transact({"from": customer})
    assert token_vault_tapped.functions.claimed(customer).call() == 400

    time_travel(chain, token_vault_tapped.functions.freezeEndsAt().call() + 2000 - 1)

    assert token.functions.balanceOf(customer_2).call() == 0
    token_vault_tapped.functions.claim().transact({"from": customer_2})
    assert token.functions.balanceOf(customer_2).call() == 2000

    assert token_vault_tapped.functions.totalClaimed().call() == 2400
