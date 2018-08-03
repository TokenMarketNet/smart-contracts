"""Rebuilding broken crowdsale contracts."""
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
def new_token(chain, team_multisig, token_name, token_symbol) -> Contract:
    """Get another token contract with 0 initial issuance."""

    args = [token_name, token_symbol, 0, 0, True]  # Owner set

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('CrowdsaleToken', deploy_args=args, deploy_transaction=tx)
    return contract


@pytest.fixture
def start_time(web3) -> int:
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
    token.functions.setMintAgent(contract.address, True).transact({"from": team_multisig})
    assert token.functions.mintAgents(contract.address).call() == True

    token.functions.setReleaseAgent(contract.address).transact({"from": team_multisig})
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

    assert contract.functions.owner().call() == team_multisig
    assert not new_token.functions.released().call()
    assert contract.functions.maximumSellableTokens().call() == cap

    # Allow crowdsale contract to do mint()
    new_token.functions.setMintAgent(contract.address, True).transact({"from": team_multisig})
    assert new_token.functions.mintAgents(contract.address).call() == True
    set_finalizer(chain, new_token, contract, team_multisig, founder_allocation)

    return contract


def test_rebuild_failed_crowdsale_with_new_token(chain, original_crowdsale, token, new_token, relaunched_crowdsale, sample_data, team_multisig, customer, customer_2):
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

    # Import old transactions from the multisig contract
    for data in sample_data:
        addr = data["Address"]
        wei = to_wei(data["Invested ETH"], "ether")
        tokens = int(data["Received tokens"])
        orig_txid = int(data["Tx hash"], 16)
        orig_tx_index = int(data["Tx index"])
        relaunched_crowdsale.functions.setInvestorDataAndIssueNewToken(
            addr, wei, tokens, orig_txid
        ).transact({"from": team_multisig})

    # No double issuance for the same tx
    data = sample_data[0]
    addr = data["Address"]
    wei = to_wei(data["Invested ETH"], "ether")
    tokens = int(data["Received tokens"])
    orig_txid = int(data["Tx hash"], 16)
    orig_tx_index = int(data["Tx index"])
    with pytest.raises(TransactionFailed):
        relaunched_crowdsale.functions.setInvestorDataAndIssueNewToken(
            addr, wei, tokens, orig_txid
        ).transact({"from": team_multisig})

    # Compare that both crowdsales and tokens look the same
    assert original_crowdsale.functions.tokensSold().call() == relaunched_crowdsale.functions.tokensSold().call()
    assert original_crowdsale.call().investedAmountOf(customer) == relaunched_crowdsale.functions.investedAmountOf(customer).call()
    assert original_crowdsale.functions.investedAmountOf(customer_2).call() == relaunched_crowdsale.functions.investedAmountOf(customer_2).call()

    assert token.functions.balanceOf(customer).call() == relaunched_crowdsale.functions.tokenAmountOf(customer).call()
    assert token.functions.balanceOf(customer_2).call() == relaunched_crowdsale.functions.tokenAmountOf(customer_2).call()
    assert token.functions.balanceOf(customer).call() == new_token.functions.balanceOf(customer).call()
    assert token.functions.balanceOf(customer_2).call() == new_token.functions.balanceOf(customer_2).call()

    assert token.functions.totalSupply().call() == new_token.functions.totalSupply().call()

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



def test_rebuild_success_crowdsale_with_new_token(chain, new_token, relaunched_crowdsale, success_sample_data, team_multisig, customer, customer_2):
    """Rebuild a crowdsale that reaches its minimum goal."""

    time_travel(chain, relaunched_crowdsale.functions.startsAt().call() + 1)
    assert relaunched_crowdsale.functions.getState().call() == CrowdsaleState.Funding

    # Import old transactions from the multisig contract
    for data in success_sample_data:
        addr = data["Address"]
        wei = to_wei(data["Invested ETH"], "ether")
        tokens = int(data["Received tokens"])
        orig_txid = int(data["Tx hash"], 16)
        # orig_tx_index = int(data["Tx index"])
        relaunched_crowdsale.functions.setInvestorDataAndIssueNewToken(
            addr, wei, tokens, orig_txid
        ).transact({"from": team_multisig})

        assert relaunched_crowdsale.functions.getRestoredTransactionStatus(orig_txid).call()

    # Compare that both crowdsales and tokens look the same
    assert relaunched_crowdsale.functions.investorCount().call() == 2

    # We restored 3 events
    events = relaunched_crowdsale.events.RestoredInvestment().createFilter(fromBlock=0).get_all_entries()
    assert len(events) == 3

    assert new_token.functions.balanceOf(customer_2).call() == 1222
    assert new_token.functions.balanceOf(customer).call() == relaunched_crowdsale.functions.tokenAmountOf(customer).call()
    assert new_token.functions.balanceOf(customer_2).call() == relaunched_crowdsale.functions.tokenAmountOf(customer_2).call()
    assert new_token.functions.totalSupply().call() == relaunched_crowdsale.functions.tokensSold().call()

    time_travel(chain, relaunched_crowdsale.functions.endsAt().call() + 1)

    assert relaunched_crowdsale.functions.getState().call() == CrowdsaleState.Success

    before_final = new_token.functions.totalSupply().call()
    relaunched_crowdsale.functions.finalize().transact({"from": team_multisig})
    assert new_token.functions.totalSupply().call() == int(before_final * 1.20)

    assert new_token.functions.released().call()
