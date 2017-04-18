"""Rebuilding broken crowdsale contracts."""
import csv
import datetime
from io import StringIO

import pytest
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
    return 4000000


@pytest.fixture
def sample_data(customer, customer_2):
    data = """
Address,First payment at,Invested ETH,Received tokens
{},2017-04-13T16:01:46+00:00,0.505,561
{},2017-04-13T16:04:33+00:00,29,32222
    """.strip().format(customer, customer_2)
    return list(csv.DictReader(StringIO(data)))


@pytest.fixture
def founder_allocation() -> float:
    """How much tokens are allocated to founders, etc."""
    return 0.2


def set_finalizer(chain, token, crowdsale, team_multisig, founder_allocation) -> Contract:
    # Create finalizer contract
    args = [
        token.address,
        crowdsale.address,
        int(founder_allocation * 10000),  # 20% for founders, bounties, etc.
        team_multisig,  # Who gets extra tokens
    ]
    contract, hash = chain.provider.deploy_contract('BonusFinalizeAgent', deploy_args=args)

    # Allow finalzier to do mint()
    token.transact({"from": team_multisig}).setMintAgent(contract.address, True)
    assert token.call().mintAgents(contract.address) == True

    token.transact({"from": team_multisig}).setReleaseAgent(contract.address)
    crowdsale.transact({"from": team_multisig}).setFinalizeAgent(contract.address)
    return contract


def set_extra_finalizer(chain, token, crowdsale, team_multisig, founder_allocation) -> Contract:
    # Create finalizer contract
    args = [
        token.address,
        crowdsale.address,
        int(founder_allocation * 10000),  # 20% for founders, bounties, etc.
        team_multisig,  # Who gets extra tokens
        (561 + 32222),
    ]
    contract, hash = chain.provider.deploy_contract('ExtraFinalizeAgent', deploy_args=args)

    # Allow finalzier to do mint()
    token.transact({"from": team_multisig}).setMintAgent(contract.address, True)
    assert token.call().mintAgents(contract.address) == True

    crowdsale.transact({"from": team_multisig}).setFinalizeAgent(contract.address)
    return contract


@pytest.fixture
def milestone_pricing(chain, start_time):
    """Milestone pricing, do not set presale collection contract."""

    week = 24*3600 * 7

    args = [
        "0x0000000000000000000000000000000000000000",
        to_wei("0.00001", "ether"),
        [
            start_time + 0, to_wei("0.0009", "ether"),
            start_time + week*1, to_wei("0.0009", "ether"),
        ],
    ]

    tx = {
        "gas": 4000000
    }
    contract, hash = chain.provider.deploy_contract('MilestonePricing', deploy_args=args, deploy_transaction=tx)
    return contract


@pytest.fixture
def original_crowdsale(chain, team_multisig, start_time, end_time, milestone_pricing, preico_cap, minimum_funding_goal, cap, token, founder_allocation) -> Contract:
    """Crowdsale that we are going to relaunch.

    This will reserve the release agent for the original crowdsale.
    """

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

    set_finalizer(chain, token, contract, team_multisig, founder_allocation)

    return contract


@pytest.fixture
def relaunched_crowdsale(chain, team_multisig, start_time, end_time, milestone_pricing, preico_cap, minimum_funding_goal, cap, original_crowdsale, token, founder_allocation) -> Contract:
    """Create a crowdsale with fixed contracts."""

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

    contract, hash = chain.provider.deploy_contract('RelaunchedCrowdsale', deploy_args=args, deploy_transaction=tx)

    assert contract.call().owner() == team_multisig
    assert not token.call().released()
    assert contract.call().maximumSellableTokens() == cap

    # Allow crowdsale contract to do mint()
    token.transact({"from": team_multisig}).setMintAgent(contract.address, True)
    assert token.call().mintAgents(contract.address) == True

    # TODO: Use dummy finalizer here
    founder_allocation = 0
    set_extra_finalizer(chain, token, contract, team_multisig, founder_allocation)

    return contract


def test_rebuild_failed_crowdsale(chain, original_crowdsale, token, relaunched_crowdsale, sample_data, team_multisig, customer, customer_2):
    """Rebuild a crowdsale that is not going to reach its minimum goal."""

    time_travel(chain, original_crowdsale.call().startsAt() + 1)
    assert original_crowdsale.call().getState() == CrowdsaleState.Funding
    assert relaunched_crowdsale.call().getState() == CrowdsaleState.Funding

    for data in sample_data:
        addr = data["Address"]
        wei = to_wei(data["Invested ETH"], "ether")
        original_crowdsale.transact({"from": addr, "value": wei}).buy()

    # We have a confirmation hash
    events = original_crowdsale.pastEvents("Invested").get()
    assert len(events) == 2
    e = events[-1]

    for data in sample_data:
        addr = data["Address"]
        wei = to_wei(data["Invested ETH"], "ether")
        tokens = int(data["Received tokens"])
        relaunched_crowdsale.transact({"from": team_multisig}).setInvestorData(addr, wei, tokens)

    assert original_crowdsale.call().tokensSold() == relaunched_crowdsale.call().tokensSold()
    assert original_crowdsale.call().investedAmountOf(customer) == relaunched_crowdsale.call().investedAmountOf(customer)
    assert original_crowdsale.call().investedAmountOf(customer_2) == relaunched_crowdsale.call().investedAmountOf(customer_2)

    assert token.call().balanceOf(customer) == relaunched_crowdsale.call().tokenAmountOf(customer)
    assert token.call().balanceOf(customer_2) == relaunched_crowdsale.call().tokenAmountOf(customer_2)

    time_travel(chain, original_crowdsale.call().endsAt() + 1)

    assert original_crowdsale.call().getState() == CrowdsaleState.Failure
    assert relaunched_crowdsale.call().getState() == CrowdsaleState.Failure
    relaunched_crowdsale.transact({"from": team_multisig, "value": to_wei(30, "ether")}).loadRefund()
    assert relaunched_crowdsale.call().getState() == CrowdsaleState.Refunding

    relaunched_crowdsale.transact({"from": customer}).refund()
    relaunched_crowdsale.transact({"from": customer_2}).refund()

    # No double refund
    with pytest.raises(TransactionFailed):
        relaunched_crowdsale.transact({"from": customer}).refund()

    with pytest.raises(TransactionFailed):
        original_crowdsale.transact({"from": customer}).refund()
