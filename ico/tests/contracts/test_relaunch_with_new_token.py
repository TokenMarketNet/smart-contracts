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
def new_token(chain, team_multisig, token_name, token_symbol) -> Contract:
    """Get another token contract with 0 initial issuance."""

    args = [token_name, token_symbol, 0, 0, True]  # Owner set

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('CrowdsaleToken', deploy_args=args, deploy_transaction=tx)
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
def cap() -> int:
    """What is our maximum tokens sold capacity."""
    return 4000000


@pytest.fixture
def sample_data(customer, customer_2):
    data = """
Address,Payment at,Tx hash,Tx index,Invested ETH,Received tokens
{},2017-04-13T16:01:46+00:00,0xf88780859cfde239e5898d036b685f5358d4b0a0f82e8cce26403c782f8a2e52,1,0.505,561
{},2017-04-13T16:02:38+00:00,0x1385320b9d693afad1dce05cb0f9c8c3c1bc017668d32ee2b69d4039fdaf5983,3,0.1,111
    """.strip().format(customer, customer_2)
    return list(csv.DictReader(StringIO(data)))


@pytest.fixture
def success_sample_data(customer, customer_2):
    """Enough to break the minimum funding goal"""
    data = """
Address,Payment at,Tx hash,Tx index,Invested ETH,Received tokens
{},2017-04-13T16:01:46+00:00,0xf88780859cfde239e5898d036b685f5358d4b0a0f82e8cce26403c782f8a2e52,1,0.505,561
{},2017-04-13T16:02:38+00:00,0x1385320b9d693afad1dce05cb0f9c8c3c1bc017668d32ee2b69d4039fdaf5983,3,0.1,111
{},2017-04-13T16:02:38+00:00,0x1385320b9d693afad1dce05cb0f9c8c3c1bc017668d32ee2b69d4039fdaf5984,4,7500,1111
    """.strip().format(customer, customer_2, customer_2)
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
def relaunched_crowdsale(chain, team_multisig, start_time, end_time, milestone_pricing, preico_cap, minimum_funding_goal, cap, original_crowdsale, new_token, founder_allocation) -> Contract:
    """Create a crowdsale with fixed contracts."""

    args = [
        new_token.address,
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
    assert not new_token.call().released()
    assert contract.call().maximumSellableTokens() == cap

    # Allow crowdsale contract to do mint()
    new_token.transact({"from": team_multisig}).setMintAgent(contract.address, True)
    assert new_token.call().mintAgents(contract.address) == True
    set_finalizer(chain, new_token, contract, team_multisig, founder_allocation)

    return contract


def test_rebuild_failed_crowdsale_with_new_token(chain, original_crowdsale, token, new_token, relaunched_crowdsale, sample_data, team_multisig, customer, customer_2):
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

    # Import old transactions from the multisig contract
    for data in sample_data:
        addr = data["Address"]
        wei = to_wei(data["Invested ETH"], "ether")
        tokens = int(data["Received tokens"])
        orig_txid = int(data["Tx hash"], 16)
        orig_tx_index = int(data["Tx index"])
        relaunched_crowdsale.transact({"from": team_multisig}).setInvestorDataAndIssueNewToken(addr, wei, tokens, orig_txid)

    # No double issuance for the same tx
    data = sample_data[0]
    addr = data["Address"]
    wei = to_wei(data["Invested ETH"], "ether")
    tokens = int(data["Received tokens"])
    orig_txid = int(data["Tx hash"], 16)
    orig_tx_index = int(data["Tx index"])
    with pytest.raises(TransactionFailed):
        relaunched_crowdsale.transact({"from": team_multisig}).setInvestorDataAndIssueNewToken(addr, wei, tokens, orig_txid)

    # Compare that both crowdsales and tokens look the same
    assert original_crowdsale.call().tokensSold() == relaunched_crowdsale.call().tokensSold()
    assert original_crowdsale.call().investedAmountOf(customer) == relaunched_crowdsale.call().investedAmountOf(customer)
    assert original_crowdsale.call().investedAmountOf(customer_2) == relaunched_crowdsale.call().investedAmountOf(customer_2)

    assert token.call().balanceOf(customer) == relaunched_crowdsale.call().tokenAmountOf(customer)
    assert token.call().balanceOf(customer_2) == relaunched_crowdsale.call().tokenAmountOf(customer_2)
    assert token.call().balanceOf(customer) == new_token.call().balanceOf(customer)
    assert token.call().balanceOf(customer_2) == new_token.call().balanceOf(customer_2)

    assert token.call().totalSupply() == new_token.call().totalSupply()

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



def test_rebuild_success_crowdsale_with_new_token(chain, new_token, relaunched_crowdsale, success_sample_data, team_multisig, customer, customer_2):
    """Rebuild a crowdsale that reaches its minimum goal."""

    time_travel(chain, relaunched_crowdsale.call().startsAt() + 1)
    assert relaunched_crowdsale.call().getState() == CrowdsaleState.Funding

    # Import old transactions from the multisig contract
    for data in success_sample_data:
        addr = data["Address"]
        wei = to_wei(data["Invested ETH"], "ether")
        tokens = int(data["Received tokens"])
        orig_txid = int(data["Tx hash"], 16)
        # orig_tx_index = int(data["Tx index"])
        relaunched_crowdsale.transact({"from": team_multisig}).setInvestorDataAndIssueNewToken(addr, wei, tokens, orig_txid)

        assert relaunched_crowdsale.call().getRestoredTransactionStatus(orig_txid)

    # Compare that both crowdsales and tokens look the same
    assert relaunched_crowdsale.call().investorCount() == 2

    # We restored 3 events
    events = relaunched_crowdsale.pastEvents("RestoredInvestment").get()
    assert len(events) == 3

    assert new_token.call().balanceOf(customer_2) == 1222
    assert new_token.call().balanceOf(customer) == relaunched_crowdsale.call().tokenAmountOf(customer)
    assert new_token.call().balanceOf(customer_2) == relaunched_crowdsale.call().tokenAmountOf(customer_2)
    assert new_token.call().totalSupply() == relaunched_crowdsale.call().tokensSold()

    time_travel(chain, relaunched_crowdsale.call().endsAt() + 1)

    assert relaunched_crowdsale.call().getState() == CrowdsaleState.Success

    before_final = new_token.call().totalSupply()
    relaunched_crowdsale.transact({"from": team_multisig}).finalize()
    assert new_token.call().totalSupply() == int(before_final * 1.20)

    assert new_token.call().released()
