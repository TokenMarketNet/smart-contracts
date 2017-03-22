"""Upgradeable token."""

import pytest
from ethereum.tester import TransactionFailed
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

    assert not token.call().canUpgrade()
    assert token.call().getUpgradeState() == UpgradeState.NotAllowed


def test_can_upgrade_released_token(released_token: Contract):
    """Released token is free to upgrade."""
    assert released_token.call().canUpgrade()
    assert released_token.call().getUpgradeState() == UpgradeState.WaitingForAgent


def test_set_upgrade_agent(released_token: Contract, upgrade_agent: Contract, team_multisig):
    """Upgrade agent can be set on a released token."""

    # Preconditions are met
    assert upgrade_agent.call().isUpgradeAgent()
    assert released_token.call().canUpgrade()
    assert released_token.call().upgradeMaster() == team_multisig
    assert upgrade_agent.call().oldToken() == released_token.address
    assert upgrade_agent.call().originalSupply() == released_token.call().totalSupply()

    released_token.transact({"from": team_multisig}).setUpgradeAgent(upgrade_agent.address)
    assert released_token.call().getUpgradeState() == UpgradeState.ReadyToUpgrade


def test_malicious_set_upgrade_agent(released_token: Contract, upgrade_agent: Contract, malicious_address):
    """Only owner can set the upgrade agent can be set on a released token."""

    with pytest.raises(TransactionFailed):
        released_token.transact({"from": malicious_address}).setUpgradeAgent(upgrade_agent.address)


def test_change_upgrade_master(released_token: Contract, upgrade_agent: Contract, team_multisig, customer):
    """Owner can change the upgrade master."""

    released_token.transact({"from": team_multisig}).setUpgradeMaster(customer)
    released_token.transact({"from": customer}).setUpgradeAgent(upgrade_agent.address)


def test_upgrade_partial(released_token: Contract, upgrade_agent: Contract, team_multisig, customer):
    """We can upgrade some of tokens."""

    released_token.transact({"from": team_multisig}).setUpgradeAgent(upgrade_agent.address)
    assert released_token.call().balanceOf(team_multisig) == 9990000
    assert released_token.call().totalSupply() == 10000000
    released_token.transact({"from": team_multisig}).upgrade(3000000)

    assert released_token.call().getUpgradeState() == UpgradeState.Upgrading

    assert released_token.call().totalSupply() == 7000000
    assert upgrade_agent.call().totalSupply() == 3000000
    assert released_token.call().totalUpgraded() == 3000000

    assert released_token.call().balanceOf(team_multisig) == 6990000
    assert upgrade_agent.call().balanceOf(team_multisig) == 3000000


def test_upgrade_all(released_token: Contract, upgrade_agent: Contract, team_multisig, customer):
    """We can upgrade all tokens of two owners."""

    released_token.transact({"from": team_multisig}).setUpgradeAgent(upgrade_agent.address)
    assert released_token.call().balanceOf(team_multisig) == 9990000
    assert released_token.call().balanceOf(customer) == 10000
    assert released_token.call().totalSupply() == 10000000
    released_token.transact({"from": team_multisig}).upgrade(9990000)
    released_token.transact({"from": customer}).upgrade(10000)

    assert released_token.call().getUpgradeState() == UpgradeState.Upgrading
    assert released_token.call().totalSupply() == 0
    assert upgrade_agent.call().totalSupply() == 10000000
    assert released_token.call().totalUpgraded() == 10000000

    assert upgrade_agent.call().balanceOf(team_multisig) == 9990000
    assert upgrade_agent.call().balanceOf(customer) == 10000


def test_cannot_upgrade_too_many(released_token: Contract, upgrade_agent: Contract, team_multisig, customer):
    """We cannot upgrade more tokens than we have."""

    released_token.transact({"from": team_multisig}).setUpgradeAgent(upgrade_agent.address)
    assert released_token.call().balanceOf(customer) == 10000

    with pytest.raises(TransactionFailed):
        released_token.transact({"from": customer}).upgrade(20000)


def test_cannot_change_agent_in_fly(released_token: Contract, upgrade_agent: Contract, team_multisig, customer, upgrade_agent_2):
    """Upgrade agent cannot be changed after the ugprade has begun."""

    released_token.transact({"from": team_multisig}).setUpgradeAgent(upgrade_agent.address)
    released_token.transact({"from": customer}).upgrade(10000)

    with pytest.raises(TransactionFailed):
        released_token.transact({"from": team_multisig}).setUpgradeAgent(upgrade_agent_2.address)

