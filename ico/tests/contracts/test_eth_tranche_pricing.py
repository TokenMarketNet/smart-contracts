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
    # 2 minutes from now
    return web3.eth.getBlock('pending').timestamp + 120


@pytest.fixture
def end_time(start_time) -> int:
    return int(start_time + 4*7*24*3600)


@pytest.fixture
def token(uncapped_token) -> Contract:
    """Token contract used in wei_tranche tests"""
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
def wei_tranche_pricing(chain, presale_fund_collector, start_time, end_time, team_multisig):
    args = [
        [
            to_wei("0", "ether"), to_wei("0.00666666", "ether"),
            to_wei("10001", "ether"), to_wei("0.00714285", "ether"),
            to_wei("30001", "ether"), to_wei("0.00769230", "ether"),
            to_wei("50001", "ether"), to_wei("0.00833333", "ether"),
            to_wei("75001", "ether"), to_wei("0.00909090", "ether"),
            to_wei("100001", "ether"), to_wei("0.01000000", "ether"),
            to_wei("1000000000", "ether"), to_wei("0.01000000", "ether"),
            to_wei("1000000000000", "ether"), to_wei("0.00", "ether")
        ],
    ]

    tx = {
        "gas": 3141592,
        "from": team_multisig
    }
    contract, hash = chain.provider.deploy_contract('EthTranchePricing', deploy_args=args, deploy_transaction=tx)

    contract.functions.setPreicoAddress(
        presale_fund_collector.address, to_wei("0.05", "ether")
    ).transact({"from": team_multisig})
    return contract


@pytest.fixture
def wei_tranche_ico(chain, team_multisig, start_time, wei_tranche_pricing, preico_cap, preico_funding_goal, token, presale_fund_collector, end_time) -> Contract:
    """Create a crowdsale contract that uses wei_tranche based pricing."""

    args = [
        token.address,
        wei_tranche_pricing.address,
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
def finalizer(chain, token, wei_tranche_ico, team_multisig) -> Contract:
    """Set crowdsale end strategy."""

    # Create finalizer contract
    args = [
        token.address,
        wei_tranche_ico.address,
    ]
    contract, hash = chain.provider.deploy_contract('DefaultFinalizeAgent', deploy_args=args)

    token.functions.setReleaseAgent(contract.address).transact({"from": team_multisig})
    wei_tranche_ico.functions.setFinalizeAgent(contract.address).transact({"from": team_multisig})
    return contract


def test_wei_tranche_getter(chain, wei_tranche_pricing, start_time):
    """Tranche data is exposed to the world."""

    amount, price = wei_tranche_pricing.call().getTranche(0)
    assert amount == 0 #Tranche amount
    assert price == 6666660000000000


def test_wei_tranche_data(chain, wei_tranche_pricing, start_time):
    """Tranche data can be read."""

    for i in range(0, 4):
        time, price = wei_tranche_pricing.functions.getTranche(i).call()
        print("-", time)
        print("-", price)


def test_wei_tranche_prices(chain, wei_tranche_pricing, start_time, end_time, customer):
    """We get correct wei_tranche prices for different dates."""

    assert wei_tranche_pricing.functions.getCurrentPrice(0).call() == 6666660000000000

    #TODO: Instead of timetravel, buy tokens here after this line, and then copy this
    assert wei_tranche_pricing.functions.calculatePrice(
        to_wei("0.00666666", "ether"),
        0,
        0,
        customer,
        0,
    ).call() == 1

    assert wei_tranche_pricing.functions.calculatePrice(
        to_wei("0.00714285", "ether"),
        to_wei("10000", "ether"),
        0,
        customer,
        0,
    ).call() == 1

    assert wei_tranche_pricing.functions.calculatePrice(
        to_wei("0.00714285", "ether"),
        to_wei("10001", "ether"),
        0,
        customer,
        0,
    ).call() == 1

    assert wei_tranche_pricing.functions.calculatePrice(
        to_wei("0.03000000", "ether"),
        to_wei("100001", "ether"),
        0,
        customer,
        0,
    ).call() == 3


def test_non_fractional_price(chain, wei_tranche_pricing, customer, end_time):
    """We divide price correctly for integer only amount."""

    assert wei_tranche_pricing.functions.calculatePrice(
        to_wei("0.01333332", "ether"),
        0,
        0,
        customer,
        0,
    ).call() == 2

    assert wei_tranche_pricing.functions.calculatePrice(
        to_wei("0.01333335", "ether"),
        0,
        0,
        customer,
        0,
    ).call() == 2

    assert wei_tranche_pricing.functions.calculatePrice(
        to_wei("0.00666666", "ether"),
        to_wei("10000", "ether"),
        0,
        customer,
        0,
    ).call() == 1

    assert wei_tranche_pricing.functions.calculatePrice(
        to_wei("0.01428570", "ether"),
        to_wei("10001", "ether"),
        0,
        customer,
        0,
    ).call() == 2

    assert wei_tranche_pricing.functions.calculatePrice(
        to_wei("0.03000000", "ether"),
        to_wei("100001", "ether"),
        0,
        customer,
        0,
    ).call() == 3


def test_wei_tranche_calculate_preico_price(chain, wei_tranche_pricing, start_time, presale_fund_collector):
    """Preico contributors get their special price."""

    # Pre-ico address always buys at the fixed price
    assert wei_tranche_pricing.call().calculatePrice(
        to_wei("0.05", "ether"),
        0,
        0,
        presale_fund_collector.address,
        0
    ) == 1


def test_presale_move_to_wei_tranche_based_crowdsale(chain, presale_fund_collector, wei_tranche_ico, finalizer, token, start_time, team_multisig, customer, customer_2):
    """When pre-ico contract funds are moved to the crowdsale, the pre-sale investors gets tokens with a preferred price and not the current wei_tranche price."""

    value = to_wei(50, "ether")
    presale_fund_collector.functions.invest().transact({"from": customer, "value": value})

    # ICO begins, Link presale to an actual ICO
    presale_fund_collector.functions.setCrowdsale(wei_tranche_ico.address).transact({"from": team_multisig})
    time_travel(chain, start_time)

    assert wei_tranche_ico.functions.getState().call() == CrowdsaleState.Funding

    # Load funds to ICO
    presale_fund_collector.functions.participateCrowdsaleAll().transact()

    # Tokens received, paid by preico price
    wei_tranche_ico.functions.investedAmountOf(customer).call() == to_wei(50, "ether")
    token.functions.balanceOf(customer).call() == 50 / 0.050


def test_fractional_preico_pricing(presale_fund_collector, wei_tranche_pricing, fractional_token):
    """Pre-ICO amount is calculated correctly for a token having fractions.

    """

    amount = wei_tranche_pricing.functions.calculatePrice(
        to_wei("0.05", "ether"),
        0,
        0,
        presale_fund_collector.address,
        fractional_token.call().decimals()
    ).call()

    assert amount == 100000000
    d = decimalize_token_amount(fractional_token, amount)

    assert d == 1

    # Make sure we get decimals right
    assert d.as_tuple() == Decimal("1.00000000").as_tuple()


def test_fractional_wei_tranche_pricing(chain, presale_fund_collector, wei_tranche_pricing, fractional_token, customer):
    """Tranche amount is calculated correctly for a token having fractions."""

    amount = wei_tranche_pricing.functions.calculatePrice(
        to_wei("0.01000000", "ether"),
        to_wei("100001", "ether"),
        0,
        customer,
        fractional_token.call().decimals()
    ).call()

    assert amount == 100000000
    d = decimalize_token_amount(fractional_token, amount)

    assert d == Decimal("1.00000000")

    # Make sure we get decimals right
    assert d.as_tuple() == Decimal("1.00000000").as_tuple()


def test_presale_update_counters(chain, presale_fund_collector, wei_tranche_ico, finalizer, token, start_time, team_multisig, customer, customer_2, wei_tranche_pricing):
    """Check that presale counters work correctly.

    Presale investments should not count against tranches giving in the retail,
    but they are only effective in the main sale.

    .. warn::

        Use PreicoProxyBuyer contract instead of PrealeFundsCollector to handle this in
        meaningful way.
    """

    # We have set up the contracts in the way the presale purchaser gets special pricing
    assert wei_tranche_ico.functions.pricingStrategy().call() == wei_tranche_pricing.address
    wei_tranche_pricing.functions.setPreicoAddress(customer, to_wei("0.05", "ether")).transact({"from": team_multisig})

    assert wei_tranche_pricing.functions.isPresalePurchase(customer).call() == True

    value = to_wei(20000, "ether")
    presale_fund_collector.functions.invest().transact({"from": customer, "value": value})

    # ICO begins, Link presale to an actual ICO
    presale_fund_collector.functions.setCrowdsale(wei_tranche_ico.address).transact({"from": team_multisig})
    time_travel(chain, start_time)

    assert wei_tranche_ico.functions.getState().call() == CrowdsaleState.Funding

    # Load funds to ICO
    presale_fund_collector.functions.participateCrowdsaleAll().transact()

    assert wei_tranche_ico.functions.weiRaised().call() == to_wei(20000, "ether")
    assert wei_tranche_ico.functions.presaleWeiRaised().call() == to_wei(20000, "ether")

    # Tokens received, paid by preico price
    assert wei_tranche_ico.functions.investedAmountOf(customer).call() == to_wei(20000, "ether")
    token.functions.balanceOf(customer).call() == 20000 / 0.040

    # Do a normal investment, should go to tranche 1, as presale investment does not
    # count against tranches
    wei_tranche_ico.functions.buy().transact({"from": customer_2, "value": to_wei(10, "ether")})
    assert wei_tranche_ico.functions.presaleWeiRaised().call() == to_wei(20000, "ether")
    assert wei_tranche_ico.functions.weiRaised().call() == to_wei(20010, "ether")
    token.functions.balanceOf(customer).call() == 10 / 0.00666666
