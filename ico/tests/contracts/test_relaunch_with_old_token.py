"""Rebuilding broken crowdsale contracts using the old token contract."""
import csv
from io import StringIO

import pytest
from eth_utils import to_wei
from eth_tester.exceptions import TransactionFailed
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.state import CrowdsaleState


@pytest.fixture
def token(empty_token):
    """Get a token with 0 initial issuance."""
    return empty_token


@pytest.fixture
def start_time(web3) -> int:
    # 1 day ahead from now
    return web3.eth.getBlock('pending').timestamp + 24 * 60 * 60


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
Address,First payment at,Invested ETH,Received tokens,Txid
{},2017-04-13T16:01:46+00:00,0.505,561,0
{},2017-04-13T16:04:33+00:00,29,32222,0
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
    token.functions.setMintAgent(contract.address, True).transact({"from": team_multisig})
    assert token.functions.mintAgents(contract.address).call() == True

    token.functions.setReleaseAgent(contract.address).transact({"from": team_multisig})
    crowdsale.functions.setFinalizeAgent(contract.address).transact({"from": team_multisig})
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
    token.functions.setMintAgent(contract.address, True).transact({"from": team_multisig})
    assert token.functions.mintAgents(contract.address).call() == True

    crowdsale.functions.setFinalizeAgent(contract.address).transact({"from": team_multisig})
    return contract


@pytest.fixture
def milestone_pricing(chain, start_time, end_time):
    """Milestone pricing, do not set presale collection contract."""

    week = 24*3600 * 7

    args = [
        [
            start_time + 0, to_wei("0.0009", "ether"),
            start_time + week*1, to_wei("0.0009", "ether"),
            end_time, 0,
        ],
    ]

    tx = {
        "gas": 3141592
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

    assert contract.functions.owner().call() == team_multisig
    assert not token.functions.released().call()
    assert contract.functions.maximumSellableTokens().call() == cap

    # Allow crowdsale contract to do mint()
    token.functions.setMintAgent(contract.address, True).transact({"from": team_multisig})
    assert token.functions.mintAgents(contract.address).call() == True

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

    assert contract.functions.owner().call() == team_multisig
    assert not token.functions.released().call()
    assert contract.functions.maximumSellableTokens().call() == cap

    # Allow crowdsale contract to do mint()
    token.functions.setMintAgent(contract.address, True).transact({"from": team_multisig})
    assert token.functions.mintAgents(contract.address).call() == True

    # TODO: Use dummy finalizer here
    founder_allocation = 0
    set_extra_finalizer(chain, token, contract, team_multisig, founder_allocation)

    return contract


def test_rebuild_failed_crowdsale(chain, original_crowdsale, token, relaunched_crowdsale, sample_data, team_multisig, customer, customer_2):
    """Rebuild a crowdsale that is not going to reach its minimum goal."""

    time_travel(chain, original_crowdsale.functions.startsAt().call() + 1)
    assert original_crowdsale.functions.getState().call() == CrowdsaleState.Funding
    assert relaunched_crowdsale.functions.getState().call() == CrowdsaleState.Funding

    for data in sample_data:
        addr = data["Address"]
        wei = to_wei(data["Invested ETH"], "ether")
        original_crowdsale.functions.buy().transact({"from": addr, "value": wei})

    # We have a confirmation hash
    events = original_crowdsale.events.Invested().createFilter(fromBlock=0).get_all_entries()
    assert len(events) == 2
    e = events[-1]

    for data in sample_data:
        addr = data["Address"]
        wei = to_wei(data["Invested ETH"], "ether")
        tokens = int(data["Received tokens"])
        txid = int(data["Txid"], 16)
        relaunched_crowdsale.functions.setInvestorData(addr, wei, tokens, txid).transact({"from": team_multisig})

    assert original_crowdsale.functions.tokensSold().call() == relaunched_crowdsale.functions.tokensSold().call()
    assert original_crowdsale.functions.investedAmountOf(
        customer).call() == relaunched_crowdsale.functions.investedAmountOf(customer).call()
    assert original_crowdsale.functions.investedAmountOf(
        customer_2).call() == relaunched_crowdsale.functions.investedAmountOf(customer_2).call()

    assert token.functions.balanceOf(customer).call() == relaunched_crowdsale.functions.tokenAmountOf(customer).call()
    assert token.functions.balanceOf(
        customer_2).call() == relaunched_crowdsale.functions.tokenAmountOf(customer_2).call()

    time_travel(chain, original_crowdsale.functions.endsAt().call() + 1)

    assert original_crowdsale.functions.getState().call() == CrowdsaleState.Failure
    assert relaunched_crowdsale.functions.getState().call() == CrowdsaleState.Failure
    relaunched_crowdsale.functions.loadRefund().transact({"from": team_multisig, "value": to_wei(30, "ether")})
    assert relaunched_crowdsale.functions.getState().call() == CrowdsaleState.Refunding

    relaunched_crowdsale.functions.refund().transact({"from": customer})
    relaunched_crowdsale.functions.refund().transact({"from": customer_2})

    # No double refund
    with pytest.raises(TransactionFailed):
        relaunched_crowdsale.functions.refund().transact({"from": customer})

    with pytest.raises(TransactionFailed):
        original_crowdsale.functions.refund().transact({"from": customer})
