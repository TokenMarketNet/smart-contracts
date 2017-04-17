"""Minted and capped crowdsale."""
import datetime

import pytest
from eth_utils import to_wei
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.state import CrowdsaleState


@pytest.fixture
def token(empty_token):
    """Get a token with 0 initial issuance."""
    return empty_token


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
def cap() -> int:
    """What is our maximum tokens sold capacity."""
    return 4000000


@pytest.fixture
def founder_allocation() -> float:
    """How much tokens are allocated to founders, etc."""
    return 0.2


@pytest.fixture
def milestone_pricing(chain, start_time):
    """Milestone pricing, do not set presale collection contract."""

    week = 24*3600 * 7

    args = [
        "0x0000000000000000000000000000000000000000",
        to_wei("0.05", "ether"),
        [
            start_time + 0, to_wei("0.10", "ether"),
            start_time + week*1, to_wei("0.12", "ether"),
            start_time + week*2, to_wei("0.13", "ether"),
            start_time + week*4, to_wei("0.13", "ether"),
        ],
    ]

    tx = {
        "gas": 4000000
    }
    contract, hash = chain.provider.deploy_contract('MilestonePricing', deploy_args=args, deploy_transaction=tx)
    return contract



@pytest.fixture
def crowdsale(chain, team_multisig, start_time, end_time, milestone_pricing, preico_cap, minimum_funding_goal, cap, token) -> Contract:
    """Create a crowdsale contract that has a minting cap and bonus % and token sold limit."""

    args = [
        token.address,
        milestone_pricing.address,
        team_multisig,
        start_time,
        end_time,
        minimum_funding_goal,
        cap
    ]

    tx = {
        "from": team_multisig,
    }

    contract, hash = chain.provider.deploy_contract('MintedTokenCappedCrowdsale', deploy_args=args, deploy_transaction=tx)

    assert contract.call().owner() == team_multisig
    assert not token.call().released()
    assert contract.call().maximumSellableTokens() == cap

    # Allow crowdsale contract to do mint()
    token.transact({"from": team_multisig}).setMintAgent(contract.address, True)
    assert token.call().mintAgents(contract.address) == True

    return contract


@pytest.fixture()
def finalizer(chain, token, crowdsale, team_multisig, founder_allocation) -> Contract:

    # Create finalizer contract
    args = [
        token.address,
        crowdsale.address,
        int(founder_allocation * 10000), # 20% for founders, bounties, etc.
        team_multisig, # Who gets extra tokens
    ]
    contract, hash = chain.provider.deploy_contract('BonusFinalizeAgent', deploy_args=args)

    # Set crowdsale finalizer

    # Allow finalzier to do mint()
    token.transact({"from": team_multisig}).setMintAgent(contract.address, True)
    assert token.call().mintAgents(contract.address) == True

    token.transact({"from": team_multisig}).setReleaseAgent(contract.address)

    crowdsale.transact({"from": team_multisig}).setFinalizeAgent(contract.address)

    return contract


def test_buy_some(chain, crowdsale, token, finalizer, start_time, end_time, team_multisig, customer, minimum_funding_goal, founder_allocation):
    """Buy some token and finalize crowdsale."""

    # Buy on first week
    time_travel(chain, start_time + 1)
    assert crowdsale.call().getState() == CrowdsaleState.Funding

    # Buy minimum funding goal
    wei_value = minimum_funding_goal
    crowdsale.transact({"from": customer, "value": wei_value}).buy()
    assert crowdsale.call().isMinimumGoalReached()

    # Close the deal
    time_travel(chain, end_time + 1)
    assert crowdsale.call().getState() == CrowdsaleState.Success
    crowdsale.transact({"from": team_multisig}).finalize()
    assert crowdsale.call().getState() == CrowdsaleState.Finalized

    customer_tokens = 7500 / 0.10

    # See that we counted bonus correctly
    assert finalizer.call().allocatedBonus() == customer_tokens * 0.2

    # See that bounty tokens do not count against tokens sold
    assert crowdsale.call().tokensSold() == customer_tokens
    assert token.call().totalSupply() == customer_tokens * (1+founder_allocation)

    # See that customers get their tokens
    assert token.call().balanceOf(customer) == crowdsale.call().tokensSold()

    # See that team multisig got our bonus tokens
    assert token.call().balanceOf(team_multisig) == crowdsale.call().tokensSold() * founder_allocation

    # Token is transferable
    assert token.call().released()


def test_buy_all(chain, crowdsale, token, finalizer, start_time, end_time, team_multisig, customer, cap, founder_allocation):
    """Buy all tokens and finalize crowdsale."""

    # Buy on first week
    time_travel(chain, start_time + 1)
    assert crowdsale.call().getState() == CrowdsaleState.Funding

    # Buy all cap
    wei_value = cap * to_wei("0.10", "ether")
    crowdsale.transact({"from": customer, "value": wei_value}).buy()
    assert crowdsale.call().isCrowdsaleFull()

    # Close the deal
    time_travel(chain, end_time + 1)
    assert crowdsale.call().getState() == CrowdsaleState.Success
    crowdsale.transact({"from": team_multisig}).finalize()
    assert crowdsale.call().getState() == CrowdsaleState.Finalized

    customer_tokens = 4000000

    # See that we counted bonus correctly
    assert finalizer.call().allocatedBonus() == 800000

    # See that bounty tokens do not count against tokens sold
    assert crowdsale.call().tokensSold() == customer_tokens
    assert token.call().totalSupply() == customer_tokens * (1 + founder_allocation)

    # See that customers get their tokens
    assert token.call().balanceOf(customer) == crowdsale.call().tokensSold()

    # See that team multisig got our bonus tokens
    assert token.call().balanceOf(team_multisig) == crowdsale.call().tokensSold() * founder_allocation

    # Token is transferable
    assert token.call().released()
