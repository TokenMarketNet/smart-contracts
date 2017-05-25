"""Preallocate tokens to investors.

Run MetalPay-like crowdsale.
"""
import datetime

import pytest
from eth_utils import to_wei
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.state import CrowdsaleState


@pytest.fixture
def token(chain, team_multisig):
    """Create a token with the initial supply."""

    amount = 66588888
    decimals = 8

    args = ["Cowbits", "COW", amount * 10**decimals, decimals, False]  # Owner set

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('BurnableCrowdsaleToken', deploy_args=args, deploy_transaction=tx)
    return contract


@pytest.fixture
def start_time() -> int:
    """Start Apr 15th"""
    return int((datetime.datetime(2017, 4, 15, 16, 00) - datetime.datetime(1970, 1, 1)).total_seconds())


@pytest.fixture
def end_time(start_time) -> int:
    """Run 4 weeks."""
    return start_time + 4 * 7 * 24 * 3600


@pytest.fixture
def minimum_funding_goal() -> int:
    """What is our minimum funding goal."""
    return to_wei(7500, "ether")


@pytest.fixture
def founder_allocation() -> float:
    """How much tokens are allocated to founders, etc."""
    return 0.2


@pytest.fixture
def pricing_strategy(chain, start_time, end_time):
    args = [1]  # 1 token = 1 eth
    contract, hash = chain.provider.deploy_contract('FlatPricing', deploy_args=args)
    return contract


@pytest.fixture
def early_investor_pool(accounts):
    """A pool where early investor tokens are collected"""
    return accounts[9]



@pytest.fixture
def crowdsale(chain, team_multisig, start_time, end_time, pricing_strategy, token, early_investor_pool) -> Contract:
    """Create a crowdsale contract that sells from approve() pool."""

    args = [
        token.address,
        pricing_strategy.address,
        team_multisig,
        start_time,
        end_time,
        0,
        team_multisig,
    ]

    tx = {
        "from": team_multisig,
    }

    contract, hash = chain.provider.deploy_contract('AllocatedCrowdsale', deploy_args=args, deploy_transaction=tx)

    assert contract.call().owner() == team_multisig
    assert not token.call().released()

    multiplier = 10**8

    # Allow crowdsale contract to sell its token
    # 30,500,000 is the sellable tokens in our case
    token.transact({"from": team_multisig}).approve(contract.address, 33588888*multiplier)
    token.transact({"from": team_multisig}).setTransferAgent(team_multisig, True)

    # Presell tokens, almost all are sold out
    assert contract.transact({"from": team_multisig}).preallocate(early_investor_pool, 3088888, 0)
    assert contract.transact({"from": team_multisig}).preallocate(early_investor_pool, 5500000, 1)
    assert contract.transact({"from": team_multisig}).preallocate(early_investor_pool, 5500000, 2)
    assert contract.transact({"from": team_multisig}).preallocate(early_investor_pool, 5500000, 3)
    assert contract.transact({"from": team_multisig}).preallocate(early_investor_pool, 14000000 - 100000, 4)

    return contract


@pytest.fixture()
def finalizer(chain, token, crowdsale, team_multisig, founder_allocation) -> Contract:

    # Create finalizer contract
    args = [
        token.address,
        crowdsale.address,
    ]
    contract, hash = chain.provider.deploy_contract('DefaultFinalizeAgent', deploy_args=args)

    # Set crowdsale finalizer

    # Allow finalzier to do mint()
    token.transact({"from": team_multisig}).setReleaseAgent(contract.address)
    crowdsale.transact({"from": team_multisig}).setFinalizeAgent(contract.address)
    return contract


def test_buy_some(chain, crowdsale, token, finalizer, start_time, end_time, team_multisig, customer, founder_allocation):
    """Buy some token and finalize crowdsale."""

    # Buy on first week
    time_travel(chain, start_time + 1)
    assert crowdsale.call().getState() == CrowdsaleState.Funding
    initial_sold = crowdsale.call().tokensSold()

    # Buy minimum funding goal
    wei_value = 1000
    crowdsale.transact({"from": customer, "value": wei_value}).buy()
    assert crowdsale.call().isMinimumGoalReached()

    # Close the deal
    time_travel(chain, end_time + 1)
    assert crowdsale.call().getState() == CrowdsaleState.Success
    crowdsale.transact({"from": team_multisig}).finalize()
    assert crowdsale.call().getState() == CrowdsaleState.Finalized

    customer_tokens = 1000 * 10**8

    # See that bounty tokens do not count against tokens sold
    assert crowdsale.call().tokensSold() == customer_tokens + initial_sold

    # See that customers get their tokens
    assert token.call().balanceOf(customer) == customer_tokens

    # Token is transferable
    assert token.call().released()


def test_buy_all(chain, crowdsale, token, finalizer, start_time, end_time, team_multisig, customer, early_investor_pool):
    """Buy all tokens and finalize crowdsale."""

    multiplier = 10**8
    assert crowdsale.call().getTokensLeft() == 100000 * multiplier
    assert token.call().balanceOf(early_investor_pool) == (33588888 - 100000) * multiplier
    assert crowdsale.call().weiRaised() == 8860000000000000
    assert crowdsale.call().tokensSold() == (33588888 - 100000) * multiplier

    # Buy on first week
    time_travel(chain, start_time + 1)
    assert crowdsale.call().getState() == CrowdsaleState.Funding

    # Buy all cap
    wei_value = int(crowdsale.call().getTokensLeft() / 10**8)
    crowdsale.transact({"from": customer, "value": wei_value}).buy()
    assert crowdsale.call().isCrowdsaleFull()

    # Close the deal
    time_travel(chain, end_time + 1)
    assert crowdsale.call().getState() == CrowdsaleState.Success
    crowdsale.transact({"from": team_multisig}).finalize()
    assert crowdsale.call().getState() == CrowdsaleState.Finalized
