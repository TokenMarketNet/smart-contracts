"""Milestone based pricing"""
import datetime

import pytest
from eth_utils import to_wei
from ethereum.tester import TransactionFailed
from web3.contract import Contract


from ico.tests.utils import time_travel


@pytest.fixture
def presale_fund_collector(chain, presale_freeze_ends_at, team_multisig) -> Contract:
    """In actual ICO, the price is doubled (for testing purposes)."""

    args = [
        team_multisig,
        presale_freeze_ends_at,
        to_wei("50", "ether"),  # Minimum presale buy in is 50 ethers

    ]
    tx = {
        "from": team_multisig,
    }
    presale_fund_collector, hash = chain.provider.deploy_contract('PresaleFundCollector', deploy_args=args, deploy_transaction=tx)
    return presale_fund_collector


@pytest.fixture
def start_time() -> int:
    return int((datetime.datetime(2017, 4, 15, 16, 00) - datetime.datetime(1970, 1, 1)).total_seconds())


@pytest.fixture
def token(uncapped_token) -> int:
    """Token contract used in milestone tests"""
    return uncapped_token


@pytest.fixture
def milestone_pricing(chain, presale_fund_collector, start_time):

    week = 24*3600 * 7

    args = [
        presale_fund_collector.address,
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
def milestone_ico(chain, beneficiary, team_multisig, start_time, milestone_pricing, preico_cap, preico_funding_goal, token, presale_fund_collector) -> Contract:
    """Create a crowdsale contract that uses milestone based pricing."""

    ends_at = start_time + 4*24*3600

    args = [
        token.address,
        milestone_pricing.address,
        team_multisig,
        beneficiary,
        start_time,
        ends_at,
        0,
    ]

    tx = {
        "from": team_multisig,
    }

    contract, hash = chain.provider.deploy_contract('UncappedCrowdsale', deploy_args=args, deploy_transaction=tx)

    assert contract.call().owner() == team_multisig
    assert not token.call().released()

    # Allow pre-ico contract to do mint()
    token.transact({"from": team_multisig}).setMintAgent(contract.address, True)
    assert token.call().mintAgents(contract.address) == True

    return contract


def test_milestone_getter(chain, milestone_pricing, start_time):
    """Milestone data is exposed to the world."""

    time, price = milestone_pricing.call().getMilestone(0)
    assert time == 1492272000
    assert price == 100000000000000000


def test_milestone_prices(chain, milestone_pricing, start_time, customer):
    """We get correct milestone prices for different dates."""

    time_travel(chain, start_time - 1)
    with pytest.raises(TransactionFailed):
        # Div by zero, crowdsale has not begin yet
        assert milestone_pricing.call().getCurrentPrice()

    time_travel(chain, start_time)
    assert milestone_pricing.call().getCurrentPrice() == to_wei("0.10", "ether")

    time_travel(chain, start_time + 1)
    assert milestone_pricing.call().getCurrentPrice() == to_wei("0.10", "ether")

    # 1 week forward
    time_travel(chain, int((datetime.datetime(2017, 4, 22, 16, 0) - datetime.datetime(1970, 1, 1)).total_seconds()))
    assert milestone_pricing.call().getCurrentPrice() == to_wei("0.12", "ether")

    # 2 week forward
    time_travel(chain, int((datetime.datetime(2017, 4, 29, 16, 0) - datetime.datetime(1970, 1, 1)).total_seconds()))
    assert milestone_pricing.call().getCurrentPrice() == to_wei("0.13", "ether")

    # See that we divide price correctly
    assert milestone_pricing.call().calculatePrice(
        to_wei("0.26", "ether"),
        0,
        0,
        customer
    ) == 2


def test_milestone_calculate_preico_price(chain, milestone_pricing, start_time, presale_fund_collector):
    """Preico contributors get their special price."""

    # 1 week forward
    time_travel(chain, int((datetime.datetime(2017, 4, 22, 16, 0) - datetime.datetime(1970, 1, 1)).total_seconds()))

    # Pre-ico address always buys at the fixed price
    assert milestone_pricing.call().calculatePrice(
        to_wei("0.05", "ether"),
        0,
        0,
        presale_fund_collector.address
    ) == 1


def test_presale_move_to_milestone_crowdsale(chain, presale_fund_collector, milestone_ico, token, start_time, team_multisig, customer, customer_2):
    """When pre-ico contract funds are moved to the crowdsale, the pre-sale investors gets tokens with a preferred price and not the current milestone price."""

    value = to_wei(50, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    # ICO begins, Link presale to an actual ICO
    presale_fund_collector.transact({"from": team_multisig}).setCrowdsale(milestone_ico.address)
    time_travel(chain, start_time)

    # Load funds to ICO
    presale_fund_collector.transact().parcipateCrowdsaleAll()

    # Tokens received, paid by preico price
    milestone_ico.call().investedAmountOf(customer) == to_wei(50, "ether")
    token.call().balanceOf(customer) == 50 / 0.050

