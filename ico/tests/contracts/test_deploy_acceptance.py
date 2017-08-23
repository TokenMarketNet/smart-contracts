"""A sample YAML deployment acceptance test."""
import os

import datetime
import pytest
import math

from decimal import Decimal

from eth_utils import from_wei
from eth_utils import to_wei

from ico.deploy import _deploy_contracts
from ico.definition import load_crowdsale_definitions
from ico.state import CrowdsaleState
from ico.tests.utils import time_travel


from web3.contract import Contract


@pytest.fixture()
def deploy_address(accounts) -> str:
    """Operational control account"""
    return accounts[0]


@pytest.fixture()
def presale_investor_1(accounts) -> str:
    """Test account planted in fake_seed_investor_data.csv"""
    return accounts[6]


@pytest.fixture()
def presale_investor_2(accounts) -> str:
    """Test account planted in fake_seed_investor_data.csv"""
    return accounts[7]


@pytest.fixture()
def presale_investor_3(accounts) -> str:
    """Test account planted in fake_seed_investor_data.csv"""
    return accounts[8]


@pytest.fixture()
def presale_investor_4(accounts) -> str:
    """Test account planted in fake_seed_investor_data.csv"""
    return accounts[9]


@pytest.fixture
def everything_deployed(project, chain, web3, accounts, deploy_address) -> dict:
    """Deploy our token plan."""
    yaml_filename = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..","crowdsales", "allocated-token-sale-acceptance-test.yml"))
    deployment_name = "testrpc"
    chain_data = load_crowdsale_definitions(yaml_filename, deployment_name)
    runtime_data, statistics, contracts = _deploy_contracts(project, chain, web3, yaml_filename, chain_data, deploy_address)
    return contracts


@pytest.fixture
def crowdsale(everything_deployed) -> Contract:
    """A fixture to get the crowdsale contract from the deployed YAML."""
    crowdsale = everything_deployed["crowdsale"]
    return crowdsale


@pytest.fixture()
def proxy_buyer_freeze_ends_at(chain, crowdsale) -> Contract:
    """When investors can reclaim."""
    return int(datetime.datetime(2017, 9, 20).timestamp())


@pytest.fixture
def proxy_buyers(project, chain, web3, customer, everything_deployed, deploy_address, proxy_buyer_freeze_ends_at, presale_investor_1, presale_investor_2, presale_investor_3, presale_investor_4):
    """Simulate the presale contracts."""

    crowdsale = everything_deployed["crowdsale"]
    pricing_strategy = everything_deployed["pricing_strategy"]

    # Presale price
    default_presale_price = from_wei(2500000000000000, "ether")

    # List of presale contracts
    proxy_buyers = [
        (presale_investor_1, "9930.441837", default_presale_price),
        (presale_investor_2, "9999", default_presale_price),# 0x6d997eDcA04282950416FA380d834f360fC36eBb
    ]

    results = []
    for investor, amount, price, in proxy_buyers:
        # Create finalizer contract
        amount = Decimal(amount)

        # Dummy presale min and max arguments
        args = [
            deploy_address,
            proxy_buyer_freeze_ends_at,
            1,  # 1 wei,
            to_wei(10000, "ether"),
            to_wei(10000, "ether"),
        ]
        proxy_buyer, hash = chain.provider.deploy_contract('PreICOProxyBuyer', deploy_args=args)

        # Load presale contract with money
        assert proxy_buyer.call().getState() == 1
        proxy_buyer.transact({"value": to_wei(amount, "ether"), "from": investor}).investWithoutId()

        # Set ICO
        proxy_buyer.transact({"from": deploy_address}).setCrowdsale(crowdsale.address)

        # Set proxy buyer contract special price
        pricing_strategy.transact({"from": deploy_address}).setPreicoAddress(proxy_buyer.address, to_wei(price, "ether"))

        # Allow proxy buyer to move money in early
        crowdsale.transact({"from": deploy_address}).setEarlyParicipantWhitelist(proxy_buyer.address, True)

        results.append(proxy_buyer)

    return results


def test_deploy_all(chain, web3, everything_deployed, proxy_buyers, presale_investor_1, presale_investor_2, presale_investor_3, presale_investor_4, customer, customer_2, deploy_address):
    """Acceptance test to verify that token sale YAML example functions properly."""

    crowdsale = everything_deployed["crowdsale"]
    pricing_strategy = everything_deployed["pricing_strategy"]
    token = everything_deployed["token"]
    team_multisig = everything_deployed["team_multisig"]
    decimals = 18

    # Load in proxy buery money before ICO starts
    assert crowdsale.call().getState() == CrowdsaleState.PreFunding

    # See we have full stock to sell minus the test buy done in the script
    test_buy = 0.01 * 400
    tokens_left = crowdsale.call().getTokensLeft() / (10**decimals)
    assert tokens_left == 70000000 - test_buy

    # Load proxy buyer money
    presale_total = 0
    for proxy_buyer in proxy_buyers:

        assert proxy_buyer.call().getState() == 1
        assert proxy_buyer.call().weiRaisedTotal() > 0

        # Calculate how much all presales raise total
        wei = proxy_buyer.call().weiRaisedTotal()
        amount = pricing_strategy.call().calculatePrice(
            wei,
            0,
            0,
            proxy_buyer.address,
            decimals
        ) / 10 ** decimals
        presale_total += amount

        proxy_buyer.transact({"from": deploy_address}).setCrowdsale(crowdsale.address)
        assert pricing_strategy.call().isPresalePurchase(proxy_buyer.address)

        # Check that the proxy buyer contract receives tokens immediately
        balance_before = web3.eth.getBalance(team_multisig.address)
        proxy_buyer.transact({"from": deploy_address}).buyForEverybody()
        balance_after = web3.eth.getBalance(team_multisig.address)

        assert balance_after > balance_before, "{} {}".format(balance_before, balance_after)

    # Presale, token amount is from the spreadsheet
    assert math.isclose(presale_total, 7971776, rel_tol=0.01)  # From spreadsheet, presale tokens

    # Both presale contracts moved in
    assert crowdsale.call().presaleWeiRaised() > to_wei(9000*2, "ether")

    # Now start the ICO
    time_travel(chain, crowdsale.call().startsAt())
    assert crowdsale.call().getState() == CrowdsaleState.Funding

    # We should start with 400 tokens/ETH
    amount = pricing_strategy.call().calculatePrice(
        to_wei("1", "ether"),
        0,
        0,
        customer,
        decimals
    )

    amount_should_be = 400 # tokens / 1 eth
    assert math.isclose(amount / (10**decimals), round(amount_should_be, decimals)) == True

    # Fill to tier 2 with tier 1 cap - presale amount
    # arguments are from the spreadsheet
    tier_1_token_amount_in_eth = int(7500000 * 0.0025)
    crowdsale.transact({"from": customer_2, "value": tier_1_token_amount_in_eth}).buy()

    # We should be tier 2 now
    assert crowdsale.call().weiRaised() > to_wei(18750, "ether")

    # Check tier 2 price
    amount = pricing_strategy.call().calculatePrice(
        to_wei("1", "ether"),
        crowdsale.call().weiRaised(),
        0,
        customer,
        decimals
    ) / 10**decimals

    amount_should_be = 366.666666 # tokens / 1 eth
    assert math.isclose(amount, amount_should_be, rel_tol=0.01) == True, "Got {} should {}".format(amount, amount_should_be)

    # Let's close it by reaching end of time
    time_travel(chain, crowdsale.call().endsAt() + 1)

    # Finalize the sale
    assert crowdsale.call().getState() == CrowdsaleState.Success
    assert token.call().balanceOf(team_multisig.address) == 0  # Company has no tokens yet
    crowdsale.transact({"from": deploy_address}).finalize()

    # Release the token
    token.transact({"from": deploy_address}).releaseTokenTransfer()
    assert token.call().released()

    # Presale investors can claim their tokens
    total_claimed_tokens = 0
    investors = [
        presale_investor_1,
        presale_investor_2,
    ]

    # In the simulation we have 1 investor address
    # on each proxy buyer contract
    for idx, proxy_buyer in enumerate(proxy_buyers):
        buyer_address = investors[idx]
        old_balance = token.call().balanceOf(buyer_address) / (10 ** decimals)
        assert old_balance == 0
        proxy_buyer.transact({"from": buyer_address}).claimAll()
        new_balance = token.call().balanceOf(buyer_address) / (10 ** decimals)
        diff = Decimal(new_balance) - Decimal(old_balance)
        total_claimed_tokens += diff

    # From spreadsheet, presale tokens
    assert math.isclose(total_claimed_tokens, 7971776, rel_tol=0.0001)
