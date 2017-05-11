"""Time vault functionality."""
import datetime

import pytest
from ethereum.tester import TransactionFailed
from web3.contract import Contract

from ico.tests.utils import time_travel


@pytest.fixture
def token(chain, team_multisig):
    args = [
        team_multisig,
        "Token",
        "TKN",
        1000000,
        0
    ]
    contract, hash = chain.provider.deploy_contract('CentrallyIssuedToken', deploy_args=args)
    assert contract.call().balanceOf(team_multisig) == 1000000
    return contract


@pytest.fixture
def unlock_time():
    """UNIX timestamp to unlock tokens 180 days in the future."""
    return int((datetime.datetime.now() + datetime.timedelta(days=180) - datetime.datetime(1970, 1, 1)).total_seconds())


@pytest.fixture
def vault(chain, team_multisig, token, unlock_time):
    """Deploy a loaded vault contract and move all tokens there."""
    args = [
        team_multisig,
        token.address,
        unlock_time
    ]

    contract, hash = chain.provider.deploy_contract('TimeVault', deploy_args=args)

    # Load all tokens to the vault
    token.transact({"from": team_multisig}).transfer(contract.address, 1000000)

    return contract


def test_unlock_early(chain, token: Contract, team_multisig: str, vault: Contract, unlock_time: int):
    """Early unlock fails."""

    assert token.call().balanceOf(team_multisig) == 0
    assert token.call().balanceOf(vault.address) == 1000000

    time_travel(chain, unlock_time - 1)
    with pytest.raises(TransactionFailed):
        vault.transact({"from": team_multisig}).unlock()


def test_unlock(chain, token: Contract, team_multisig: str, vault: Contract, unlock_time: int):
    """Unlock tokens."""

    assert token.call().balanceOf(team_multisig) == 0
    assert token.call().balanceOf(vault.address) == 1000000

    time_travel(chain, unlock_time + 1)
    vault.transact({"from": team_multisig}).unlock()

    assert token.call().balanceOf(team_multisig) == 1000000
    assert token.call().balanceOf(vault.address) == 0


