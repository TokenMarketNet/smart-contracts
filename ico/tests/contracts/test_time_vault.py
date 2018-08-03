"""Time vault functionality."""
import datetime

import pytest
from eth_tester.exceptions import TransactionFailed
from web3.contract import Contract

from ico.tests.utils import time_travel


@pytest.fixture
def token(chain, team_multisig):
    args = [
        team_multisig,
        "Token",
        "TKN",
        1000000,
        0,
        chain.web3.eth.getBlock('pending').timestamp + 1
    ]
    contract, hash = chain.provider.deploy_contract('CentrallyIssuedToken', deploy_args=args)
    assert contract.functions.balanceOf(team_multisig).call() == 1000000

    contract.functions.releaseTokenTransfer().transact({"from": team_multisig})
    return contract


@pytest.fixture
def unlock_time(web3):
    """UNIX timestamp to unlock tokens 180 days in the future."""
    return web3.eth.getBlock('pending').timestamp + 180 * 24 * 60 * 60


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
    token.functions.transfer(contract.address, 1000000).transact({"from": team_multisig})

    return contract


def test_unlock_early(chain, token: Contract, team_multisig: str, vault: Contract, unlock_time: int):
    """Early unlock fails."""

    assert token.functions.balanceOf(team_multisig).call() == 0
    assert token.functions.balanceOf(vault.address).call() == 1000000

    time_travel(chain, unlock_time - (24 * 60 * 60))  # FIXME: find the exact time to subtract
    with pytest.raises(TransactionFailed):
        vault.functions.unlock().transact({"from": team_multisig})


def test_unlock(chain, token: Contract, team_multisig: str, vault: Contract, unlock_time: int):
    """Unlock tokens."""

    assert token.functions.balanceOf(team_multisig).call() == 0
    assert token.functions.balanceOf(vault.address).call() == 1000000

    time_travel(chain, unlock_time + 1)
    vault.functions.unlock().transact({"from": team_multisig})

    assert token.functions.balanceOf(team_multisig).call() == 1000000
    assert token.functions.balanceOf(vault.address).call() == 0
