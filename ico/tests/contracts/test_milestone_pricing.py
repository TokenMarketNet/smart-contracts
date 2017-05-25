"""Milestone based pricing"""
import datetime

import pytest
from decimal import Decimal
from eth_utils import to_wei
from ethereum.tester import TransactionFailed
from web3.contract import Contract


from ico.tests.utils import time_travel
from ico.state import CrowdsaleState
from ico.utils import decimalize_token_amount


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
def end_time(start_time) -> int:
    return int(start_time + 4*7*24*3600)


@pytest.fixture
def token(uncapped_token) -> Contract:
    """Token contract used in milestone tests"""
    return uncapped_token


@pytest.fixture
def fractional_token(chain, token_name, token_symbol, team_multisig) -> Contract:
    """Token contract having 8 decimal places."""

    args = [token_name, token_symbol, 0, 8, True]  # Owner set

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('CrowdsaleToken', deploy_args=args, deploy_transaction=tx)
    return contract


@pytest.fixture
def milestone_pricing(chain, presale_fund_collector, start_time, end_time, team_multisig):

    week = 24*3600*7

    args = [
        [
            start_time + 0, to_wei("0.10", "ether"),
            start_time + week*1, to_wei("0.12", "ether"),
            start_time + week*2, to_wei("0.13", "ether"),
            start_time + week*3, to_wei("0.14", "ether"),
            end_time, to_wei("0", "ether"),
        ],
    ]

    tx = {
        "gas": 4000000,
        "from": team_multisig
    }
    contract, hash = chain.provider.deploy_contract('MilestonePricing', deploy_args=args, deploy_transaction=tx)

    contract.transact({"from": team_multisig}).setPreicoAddress(presale_fund_collector.address, to_wei("0.05", "ether"))
    return contract


@pytest.fixture
def milestone_ico(chain, team_multisig, start_time, milestone_pricing, preico_cap, preico_funding_goal, token, presale_fund_collector, end_time) -> Contract:
    """Create a crowdsale contract that uses milestone based pricing."""

    args = [
        token.address,
        milestone_pricing.address,
        team_multisig,
        start_time,
        end_time,
        0,
    ]

    tx = {
        "from": team_multisig,
    }

    contract, hash = chain.provider.deploy_contract('UncappedCrowdsale', deploy_args=args, deploy_transaction=tx)

    assert contract.call().owner() == team_multisig
    assert not token.call().released()

    # Allow crowdsale contract to do mint()
    token.transact({"from": team_multisig}).setMintAgent(contract.address, True)
    assert token.call().mintAgents(contract.address) == True

    return contract


@pytest.fixture()
def finalizer(chain, token, milestone_ico, team_multisig) -> Contract:
    """Set crowdsale end strategy."""

    # Create finalizer contract
    args = [
        token.address,
        milestone_ico.address,
    ]
    contract, hash = chain.provider.deploy_contract('DefaultFinalizeAgent', deploy_args=args)

    token.transact({"from": team_multisig}).setReleaseAgent(contract.address)
    milestone_ico.transact({"from": team_multisig}).setFinalizeAgent(contract.address)
    return contract


def test_milestone_getter(chain, milestone_pricing, start_time):
    """Milestone data is exposed to the world."""

    time, price = milestone_pricing.call().getMilestone(0)
    assert time == 1492272000
    assert price == 100000000000000000


def test_milestone_data(chain, milestone_pricing, start_time):
    """Milestone data can be read."""

    for i in range(0, 4):
        time, price = milestone_pricing.call().getMilestone(i)
        print("-", time)
        print("-", price)


def test_milestone_prices(chain, milestone_pricing, start_time, end_time, customer):
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

    # 3 week forward + last second
    time_travel(chain, end_time - 1)
    assert milestone_pricing.call().getCurrentPrice() == to_wei("0.14", "ether")


def test_non_fractional_price(chain, milestone_pricing, customer, end_time):
    """We divide price correctly for integer only amount."""
    time_travel(chain, end_time - 1)

    assert milestone_pricing.call().calculatePrice(
        to_wei("0.28", "ether"),
        0,
        0,
        customer,
        0,
    ) == 2

    assert milestone_pricing.call().calculatePrice(
        to_wei("0.281", "ether"),
        0,
        0,
        customer,
        0,
    ) == 2

    assert milestone_pricing.call().calculatePrice(
        to_wei("0.4199", "ether"),
        0,
        0,
        customer,
        0,
    ) == 2

    assert milestone_pricing.call().calculatePrice(
        to_wei("0.42", "ether"),
        0,
        0,
        customer,
        0,
    ) == 3


def test_milestone_calculate_preico_price(chain, milestone_pricing, start_time, presale_fund_collector):
    """Preico contributors get their special price."""

    # 1 week forward
    time_travel(chain, int((datetime.datetime(2017, 4, 22, 16, 0) - datetime.datetime(1970, 1, 1)).total_seconds()))

    # Pre-ico address always buys at the fixed price
    assert milestone_pricing.call().calculatePrice(
        to_wei("0.05", "ether"),
        0,
        0,
        presale_fund_collector.address,
        0
    ) == 1


def test_presale_move_to_milestone_based_crowdsale(chain, presale_fund_collector, milestone_ico, finalizer, token, start_time, team_multisig, customer, customer_2):
    """When pre-ico contract funds are moved to the crowdsale, the pre-sale investors gets tokens with a preferred price and not the current milestone price."""

    value = to_wei(50, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    # ICO begins, Link presale to an actual ICO
    presale_fund_collector.transact({"from": team_multisig}).setCrowdsale(milestone_ico.address)
    time_travel(chain, start_time)

    assert milestone_ico.call().getState() == CrowdsaleState.Funding

    # Load funds to ICO
    presale_fund_collector.transact().parcipateCrowdsaleAll()

    # Tokens received, paid by preico price
    milestone_ico.call().investedAmountOf(customer) == to_wei(50, "ether")
    token.call().balanceOf(customer) == 50 / 0.050


def test_fractional_preico_pricing(presale_fund_collector, milestone_pricing, fractional_token):
    """Pre-ICO amount is calculated correctly for a token having fractions.

    """

    amount = milestone_pricing.call().calculatePrice(
        to_wei("0.05", "ether"),
        0,
        0,
        presale_fund_collector.address,
        fractional_token.call().decimals()
    )

    assert amount == 100000000
    d = decimalize_token_amount(fractional_token, amount)

    assert d == 1

    # Make sure we get decimals right
    assert d.as_tuple() == Decimal("1.00000000").as_tuple()


def test_fractional_milestone_pricing(chain, presale_fund_collector, milestone_pricing, fractional_token, customer):
    """Milestone amount is calculated correctly for a token having fractions."""

    time_travel(chain, milestone_pricing.call().getPricingStartsAt() + 1)

    amount = milestone_pricing.call().calculatePrice(
        to_wei("0.512345678", "ether"),
        0,
        0,
        customer,
        fractional_token.call().decimals()
    )

    assert amount == 512345678
    d = decimalize_token_amount(fractional_token, amount)

    assert d == Decimal("5.12345678")

    # Make sure we get decimals right
    assert d.as_tuple() == Decimal("5.12345678").as_tuple()
