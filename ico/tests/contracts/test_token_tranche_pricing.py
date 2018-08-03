"""Tranche based pricing"""
import pytest
from decimal import Decimal
from eth_utils import to_wei
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
def start_time(web3) -> int:
    return web3.eth.getBlock('pending').timestamp + 24 * 60 * 60


@pytest.fixture
def end_time(start_time) -> int:
    return int(start_time + 4*7*24*3600)


@pytest.fixture
def token(uncapped_token) -> Contract:
    """Token contract used in tranche tests"""
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
def tranche_pricing(chain, presale_fund_collector, start_time, end_time, team_multisig):

    week = 24*3600*7

    args = [
        [
            0, to_wei("0.10", "ether"),
            123, to_wei("0.12", "ether"),
            1234, to_wei("0.13", "ether"),
            12345, to_wei("0.14", "ether"),
            123456, to_wei("0", "ether"),
        ],
    ]

    tx = {
        "gas": 3141592,
        "from": team_multisig
    }
    contract, hash = chain.provider.deploy_contract('TokenTranchePricing', deploy_args=args, deploy_transaction=tx)

    contract.functions.setPreicoAddress(
        presale_fund_collector.address, to_wei("0.05", "ether")
    ).transact({"from": team_multisig})
    return contract


@pytest.fixture
def tranche_ico(chain, team_multisig, start_time, tranche_pricing, preico_cap, preico_funding_goal, token, presale_fund_collector, end_time) -> Contract:
    """Create a crowdsale contract that uses tranche based pricing."""

    args = [
        token.address,
        tranche_pricing.address,
        team_multisig,
        start_time,
        end_time,
        0,
    ]

    tx = {
        "from": team_multisig,
    }

    contract, hash = chain.provider.deploy_contract('UncappedCrowdsale', deploy_args=args, deploy_transaction=tx)

    assert contract.functions.owner().call() == team_multisig
    assert not token.functions.released().call()

    # Allow crowdsale contract to do mint()
    token.functions.setMintAgent(contract.address, True).transact({"from": team_multisig})
    assert token.functions.mintAgents(contract.address).call() == True

    return contract


@pytest.fixture()
def finalizer(chain, token, tranche_ico, team_multisig) -> Contract:
    """Set crowdsale end strategy."""

    # Create finalizer contract
    args = [
        token.address,
        tranche_ico.address,
    ]
    contract, hash = chain.provider.deploy_contract('DefaultFinalizeAgent', deploy_args=args)

    token.functions.setReleaseAgent(contract.address).transact({"from": team_multisig})
    tranche_ico.functions.setFinalizeAgent(contract.address).transact({"from": team_multisig})
    return contract


def test_tranche_getter(chain, tranche_pricing, start_time):
    """Tranche data is exposed to the world."""

    amount, price = tranche_pricing.functions.getTranche(0).call()
    assert amount == 0 #Tranche amount
    assert price == 100000000000000000


def test_tranche_data(chain, tranche_pricing, start_time):
    """Tranche data can be read."""

    for i in range(0, 4):
        time, price = tranche_pricing.functions.getTranche(i).call()
        print("-", time)
        print("-", price)


def test_tranche_prices(chain, tranche_pricing, start_time, end_time, customer):
    """We get correct tranche prices for different dates."""

    #TODO: Instead of timetravel, buy tokens here after this line, and then copy this
    assert tranche_pricing.functions.calculatePrice(
        to_wei("0.10", "ether"),
        0,
        0,
        customer,
        0,
    ).call() == 1

    assert tranche_pricing.functions.calculatePrice(
        to_wei("0.10", "ether"),
        122,
        0,
        customer,
        0,
    ).call() == 1

    assert tranche_pricing.functions.calculatePrice(
        to_wei("0.12", "ether"),
        123,
        0,
        customer,
        0,
    ).call() == 1

    assert tranche_pricing.functions.calculatePrice(
        to_wei("0.39", "ether"),
        1234,
        0,
        customer,
        0,
    ).call() == 3


def test_non_fractional_price(chain, tranche_pricing, customer, end_time):
    """We divide price correctly for integer only amount."""

    assert tranche_pricing.functions.calculatePrice(
        to_wei("0.28", "ether"),
        0,
        0,
        customer,
        0,
    ).call() == 2

    assert tranche_pricing.functions.calculatePrice(
        to_wei("0.281", "ether"),
        0,
        0,
        customer,
        0,
    ).call() == 2

    assert tranche_pricing.functions.calculatePrice(
        to_wei("0.11", "ether"),
        122,
        0,
        customer,
        0,
    ).call() == 1

    assert tranche_pricing.functions.calculatePrice(
        to_wei("0.25", "ether"),
        0,
        123,
        customer,
        0,
    ).call() == 2

    assert tranche_pricing.functions.calculatePrice(
        to_wei("0.40", "ether"),
        0,
        1234,
        customer,
        0,
    ).call() == 3


def test_tranche_calculate_preico_price(chain, tranche_pricing, start_time, presale_fund_collector):
    """Preico contributors get their special price."""

    # Pre-ico address always buys at the fixed price
    assert tranche_pricing.functions.calculatePrice(
        to_wei("0.05", "ether"),
        0,
        0,
        presale_fund_collector.address,
        0
    ).call() == 1


def test_presale_move_to_tranche_based_crowdsale(chain, presale_fund_collector, tranche_ico, finalizer, token, start_time, team_multisig, customer, customer_2):
    """When pre-ico contract funds are moved to the crowdsale, the pre-sale investors gets tokens with a preferred price and not the current tranche price."""

    value = to_wei(50, "ether")
    presale_fund_collector.functions.invest().transact({"from": customer, "value": value})

    # ICO begins, Link presale to an actual ICO
    presale_fund_collector.functions.setCrowdsale(tranche_ico.address).transact({"from": team_multisig})
    time_travel(chain, start_time)

    assert tranche_ico.functions.getState().call() == CrowdsaleState.Funding

    # Load funds to ICO
    presale_fund_collector.transact().participateCrowdsaleAll()

    # Tokens received, paid by preico price
    assert tranche_ico.functions.investedAmountOf(customer).call() == to_wei(50, "ether")
    assert token.functions.balanceOf(customer).call() == 50 / 0.050


def test_fractional_preico_pricing(presale_fund_collector, tranche_pricing, fractional_token):
    """Pre-ICO amount is calculated correctly for a token having fractions.

    """

    amount = tranche_pricing.call().calculatePrice(
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


def test_fractional_tranche_pricing(chain, presale_fund_collector, tranche_pricing, fractional_token, customer):
    """Tranche amount is calculated correctly for a token having fractions."""

    amount = tranche_pricing.functions.calculatePrice(
        to_wei("0.512345678", "ether"),
        0,
        0,
        customer,
        fractional_token.call().decimals()
    ).call()

    assert amount == 512345678
    d = decimalize_token_amount(fractional_token, amount)

    assert d == Decimal("5.12345678")

    # Make sure we get decimals right
    assert d.as_tuple() == Decimal("5.12345678").as_tuple()
