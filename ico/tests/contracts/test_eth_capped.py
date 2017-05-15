"""Token capped crowdsale."""
import datetime

import pytest
from eth_utils import from_wei
from eth_utils import to_wei
from ethereum.tester import TransactionFailed
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
    return to_wei(888888, "ether")


@pytest.fixture
def founder_allocation() -> float:
    """How much tokens are allocated to founders, etc."""
    return 7.0/3.0


@pytest.fixture
def pricing_strategy(chain, start_time, end_time, team_multisig):

    week = 24*3600 * 7

    args = [
       to_wei(1, "ether")
    ]

    tx = {
        "from": team_multisig,
    }

    contract, hash = chain.provider.deploy_contract('FlatPricing', deploy_args=args, deploy_transaction=tx)
    return contract


@pytest.fixture
def crowdsale(chain, team_multisig, start_time, end_time, pricing_strategy, preico_cap, minimum_funding_goal, cap, token) -> Contract:
    """Create a crowdsale contract that has a minting cap and bonus % and token sold limit."""

    args = [
        token.address,
        pricing_strategy.address,
        team_multisig,
        start_time,
        end_time,
        minimum_funding_goal,
        cap
    ]

    tx = {
        "from": team_multisig,
    }

    contract, hash = chain.provider.deploy_contract('MintedEthCappedCrowdsale', deploy_args=args, deploy_transaction=tx)

    assert contract.call().owner() == team_multisig
    assert not token.call().released()
    assert contract.call().weiCap() == cap

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


def test_buy_all(chain, web3, crowdsale, token, finalizer, start_time, end_time, team_multisig, customer, cap, founder_allocation):
    """Buy all tokens and finalize crowdsale."""

    # Buy on first week
    time_travel(chain, start_time + 1)
    assert crowdsale.call().getState() == CrowdsaleState.Funding

    # Buy all cap
    wei_value = cap
    print(from_wei(web3.eth.getBalance(customer), "ether"))
    crowdsale.transact({"from": customer, "value": wei_value}).buy()
    assert crowdsale.call().isCrowdsaleFull()

    # Close the deal
    time_travel(chain, end_time + 1)
    assert crowdsale.call().getState() == CrowdsaleState.Success
    crowdsale.transact({"from": team_multisig}).finalize()
    assert crowdsale.call().getState() == CrowdsaleState.Finalized

    # See that we counted bonus correctly
    team_bonus = token.call().totalSupply() * 7 / 10
    assert abs(finalizer.call().allocatedBonus() - team_bonus) < 10  # We lose some in decimal rounding

    # Token is transferable
    assert token.call().released()


def test_buy_all_plus_one(chain, web3, crowdsale, token, finalizer, start_time, end_time, team_multisig, customer, cap, founder_allocation):
    """Buy too many tokens."""

    # Buy on first week
    time_travel(chain, start_time + 1)
    assert crowdsale.call().getState() == CrowdsaleState.Funding

    # Buy all cap
    wei_value = cap + 1
    with pytest.raises(TransactionFailed):
        crowdsale.transact({"from": customer, "value": wei_value}).buy()
