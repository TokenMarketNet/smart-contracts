"""Upgradeable token."""

import pytest
from eth_tester.exceptions import TransactionFailed
from populus.chain import TesterChain
from web3.contract import Contract

from ico.state import UpgradeState


@pytest.fixture
def upgrade_agent(chain, released_token) -> Contract:
    """The test upgrade agent/target token."""
    args = [
        released_token.address,
    ]
    contract, hash = chain.provider.deploy_contract('TestMigrationTarget', deploy_args=args)
    return contract


@pytest.fixture
def upgrade_agent_2(chain, released_token) -> Contract:
    """Another deployment of the upgrade agent."""
    args = [
        released_token.address,
    ]
    contract, hash = chain.provider.deploy_contract('TestMigrationTarget', deploy_args=args)
    return contract


def test_cannot_upgrade_until_released(token: Contract):
    """Non-released tokens cannot be upgradeable."""

    assert not token.functions.canUpgrade().call()
    assert token.functions.getUpgradeState().call() == UpgradeState.NotAllowed


def test_can_upgrade_released_token(released_token: Contract):
    """Released token is free to upgrade."""
    assert released_token.functions.canUpgrade().call()
    assert released_token.functions.getUpgradeState().call() == UpgradeState.WaitingForAgent


def test_set_upgrade_agent(chain: TesterChain, released_token: Contract, upgrade_agent: Contract, team_multisig):
    """Upgrade agent can be set on a released token."""

    # Preconditions are met
    assert upgrade_agent.functions.isUpgradeAgent().call()
    assert released_token.functions.canUpgrade().call()
    assert released_token.functions.upgradeMaster().call() == team_multisig
    assert upgrade_agent.functions.oldToken().call() == released_token.address
    assert upgrade_agent.functions.originalSupply().call() == released_token.functions.totalSupply().call()

    released_token.transact({"from": team_multisig}).setUpgradeAgent(upgrade_agent.address)
    assert released_token.functions.getUpgradeState().call() == UpgradeState.ReadyToUpgrade


def test_malicious_set_upgrade_agent(released_token: Contract, upgrade_agent: Contract, malicious_address):
    """Only owner can set the upgrade agent can be set on a released token."""

    with pytest.raises(TransactionFailed):
        released_token.functions.setUpgradeAgent(upgrade_agent.address).transact({"from": malicious_address})


def test_change_upgrade_master(released_token: Contract, upgrade_agent: Contract, team_multisig, customer):
    """Owner can change the upgrade master."""

    released_token.functions.setUpgradeMaster(customer).transact({"from": team_multisig})
    released_token.functions.setUpgradeAgent(upgrade_agent.address).transact({"from": customer})


def test_upgrade_partial(released_token: Contract, upgrade_agent: Contract, team_multisig, customer):
    """We can upgrade some of tokens."""

    released_token.functions.setUpgradeAgent(upgrade_agent.address).transact({"from": team_multisig})
    assert released_token.functions.balanceOf(team_multisig).call() == 9990000
    assert released_token.functions.totalSupply().call() == 10000000
    released_token.functions.upgrade(3000000).transact({"from": team_multisig})

    assert released_token.functions.getUpgradeState().call() == UpgradeState.Upgrading

    assert released_token.functions.totalSupply().call() == 7000000
    assert upgrade_agent.functions.totalSupply().call() == 3000000
    assert released_token.functions.totalUpgraded().call() == 3000000

    assert released_token.functions.balanceOf(team_multisig).call() == 6990000
    assert upgrade_agent.functions.balanceOf(team_multisig).call() == 3000000


def test_upgrade_all(released_token: Contract, upgrade_agent: Contract, team_multisig, customer):
    """We can upgrade all tokens of two owners."""

    released_token.functions.setUpgradeAgent(upgrade_agent.address).transact({"from": team_multisig})
    assert released_token.functions.balanceOf(team_multisig).call() == 9990000
    assert released_token.functions.balanceOf(customer).call() == 10000
    assert released_token.functions.totalSupply().call() == 10000000
    released_token.functions.upgrade(9990000).transact({"from": team_multisig})
    released_token.functions.upgrade(10000).transact({"from": customer})

    assert released_token.functions.getUpgradeState().call() == UpgradeState.Upgrading
    assert released_token.functions.totalSupply().call() == 0
    assert upgrade_agent.functions.totalSupply().call() == 10000000
    assert released_token.functions.totalUpgraded().call() == 10000000

    assert upgrade_agent.functions.balanceOf(team_multisig).call() == 9990000
    assert upgrade_agent.functions.balanceOf(customer).call() == 10000


def test_cannot_upgrade_too_many(released_token: Contract, upgrade_agent: Contract, team_multisig, customer):
    """We cannot upgrade more tokens than we have."""

    released_token.functions.setUpgradeAgent(upgrade_agent.address).transact({"from": team_multisig})
    assert released_token.functions.balanceOf(customer).call() == 10000

    with pytest.raises(TransactionFailed):
        released_token.functions.upgrade(20000).transact({"from": customer})


def test_cannot_change_agent_in_fly(released_token: Contract, upgrade_agent: Contract, team_multisig, customer, upgrade_agent_2):
    """Upgrade agent cannot be changed after the ugprade has begun."""

    released_token.functions.setUpgradeAgent(upgrade_agent.address).transact({"from": team_multisig})
    released_token.functions.upgrade(10000).transact({"from": customer})

    with pytest.raises(TransactionFailed):
        released_token.functions.setUpgradeAgent(upgrade_agent_2.address).transact({"from": team_multisig})

