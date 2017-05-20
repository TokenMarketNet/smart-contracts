"""Preico proxy buy."""
import datetime

import pytest
from eth_utils import from_wei
from eth_utils import to_wei
from ethereum.tester import TransactionFailed
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.utils import get_constructor_arguments
from ico.state import CrowdsaleState

@pytest.fixture()
def finalizer(chain, presale_crowdsale, uncapped_token, team_multisig) -> Contract:
    """Set crowdsale end strategy."""

    # Create finalizer contract
    args = [
        uncapped_token.address,
        presale_crowdsale.address,
    ]
    contract, hash = chain.provider.deploy_contract('DefaultFinalizeAgent', deploy_args=args)
    uncapped_token.transact({"from": team_multisig}).setReleaseAgent(contract.address)
    return contract


@pytest.fixture()
def crowdsale(chain, uncapped_flatprice, uncapped_token, team_multisig, finalizer) -> Contract:
    """Crowdsale used intests.."""
    uncapped_flatprice.transact({"from": team_multisig}).setFinalizeAgent(finalizer.address)

    assert uncapped_flatprice.call().isFinalizerSane()
    assert uncapped_flatprice.call().isPricingSane()

    time_travel(chain, uncapped_flatprice.call().startsAt() + 1)
    assert uncapped_flatprice.call().getState() == CrowdsaleState.Funding

    return uncapped_flatprice


@pytest.fixture()
def token(chain, uncapped_token, team_multisig) -> Contract:
    """Token used in tests"""
    return uncapped_token


@pytest.fixture()
def proxy_buyer_freeze_ends_at(chain, crowdsale) -> Contract:
    """When investors can reclaim."""
    return crowdsale.call().endsAt() + 1


@pytest.fixture()
def proxy_buyer(chain, uncapped_token, proxy_buyer_freeze_ends_at, team_multisig) -> Contract:
    """Token used in tests"""

    # Create finalizer contract
    args = [
        team_multisig,
        proxy_buyer_freeze_ends_at,
        1,  # 1 wei
    ]
    contract, hash = chain.provider.deploy_contract('PreICOProxyBuyer', deploy_args=args)
    return contract


def test_proxy_buy(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Buy proxy as customer."""

    assert proxy_buyer.call().getState() == 1

    proxy_buyer.transact({"value": to_wei(10000, "ether"), "from": customer}).invest()
    proxy_buyer.transact({"value": to_wei(20000, "ether"), "from": customer_2}).invest()

    # Everything funder
    assert proxy_buyer.call().weiRaisedTotal() == to_wei(30000, "ether")
    assert web3.eth.getBalance(proxy_buyer.address) == to_wei(30000, "ether")
    assert proxy_buyer.call().balances(customer) == to_wei(10000, "ether")
    assert proxy_buyer.call().balances(customer_2) == to_wei(20000, "ether")

    # Move over
    assert crowdsale.call().getState() == CrowdsaleState.Funding
    proxy_buyer.transact({"from": team_multisig}).setCrowdsale(crowdsale.address)
    assert proxy_buyer.call().crowdsale() == crowdsale.address
    proxy_buyer.transact({"from": customer}).buyForEverybody()

    # We got our tokens
    assert proxy_buyer.call().getState() == 2
    assert proxy_buyer.call().tokensBought() == 36000000
    assert proxy_buyer.call().getClaimAmount(customer) == 36000000/3*1
    assert proxy_buyer.call().getClaimLeft(customer) == 36000000/3*1
    assert proxy_buyer.call().getClaimAmount(customer_2) == 36000000/3*2
    assert proxy_buyer.call().getClaimLeft(customer_2) == 36000000/3*2

    # Tokens cannot be claimed before they are released
    time_travel(chain, crowdsale.call().endsAt()+1)
    crowdsale.transact({"from": team_multisig}).finalize()
    assert token.call().released()

    # Claim tokens
    proxy_buyer.transact({"from": customer}).claimAll()
    proxy_buyer.transact({"from": customer_2}).claimAll()

    # Check investors got their tokens
    assert proxy_buyer.call().totalClaimed() == 36000000
    assert proxy_buyer.call().claimCount() == 2
    assert proxy_buyer.call().claimed(customer) == 36000000 / 3 * 1
    assert proxy_buyer.call().claimed(customer_2) == 36000000 / 3 * 2
    assert token.call().balanceOf(customer) == 36000000/3*1
    assert token.call().balanceOf(customer_2) == 36000000/3*2




