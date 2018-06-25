import datetime

import pytest
from eth_utils import to_wei
from web3.contract import Contract


@pytest.fixture
def presale_freeze_ends_at() -> int:
    """How long presale funds stay frozen until refund."""
    return int(datetime.datetime(2017, 1, 1).timestamp())


@pytest.fixture
def presale_milestone_pricing(chain, presale_fund_collector, uncapped_flatprice, presale_freeze_ends_at, team_multisig):
    """Pricing used in presale tests, allowing us to set special price for presale participants."""

    week = 24 * 3600 * 7
    start_time = uncapped_flatprice.call().startsAt()
    end_time = start_time + week*4

    uncapped_flatprice.transact({"from": team_multisig}).setEndsAt(end_time)

    args = [
        [
            start_time + 0, to_wei("0.10", "ether"),
            start_time + week*1, to_wei("0.10", "ether"),
            start_time + week*2, to_wei("0.10", "ether"),
            start_time + week*3, to_wei("0.10", "ether"),
            end_time, to_wei("0", "ether"),
        ],
    ]

    tx = {
        "gas": 4000000,
        "from": team_multisig
    }
    contract, hash = chain.provider.deploy_contract('MilestonePricing', deploy_args=args, deploy_transaction=tx)
    contract.transact({"from": team_multisig}).setPreicoAddress(presale_fund_collector.address, to_wei("0.05", "ether"))

    assert contract.call().isSane(uncapped_flatprice.address)
    return contract


@pytest.fixture
def presale_fund_collector(chain, presale_freeze_ends_at, team_multisig) -> Contract:
    """In actual ICO, the price is doubled (for testing purposes)."""
    args = [
        team_multisig,
        presale_freeze_ends_at,
        to_wei(1, "ether")
    ]
    tx = {
        "from": team_multisig,
    }
    presale_fund_collector, hash = chain.provider.deploy_contract('PresaleFundCollector', deploy_args=args, deploy_transaction=tx)
    return presale_fund_collector


@pytest.fixture
def presale_crowdsale(chain, presale_fund_collector, uncapped_flatprice, team_multisig):
    """ICO associated with the presale where funds will be moved to a presale."""
    presale_fund_collector.transact({"from": team_multisig}).setCrowdsale(uncapped_flatprice.address)
    return uncapped_flatprice


@pytest.fixture
def presale_crowdsale_miletstoned(chain, presale_fund_collector, uncapped_flatprice, presale_milestone_pricing, team_multisig):
    """ICO associated with the presale where funds will be moved to a presale.

    We set a special milestone pricing that allows us to control the pricing for the presale participants.
    """
    uncapped_flatprice.transact({"from": team_multisig}).setPricingStrategy(presale_milestone_pricing.address)
    presale_fund_collector.transact({"from": team_multisig}).setCrowdsale(uncapped_flatprice.address)
    presale_milestone_pricing.transact({"from" : team_multisig}).setPreicoAddress(presale_fund_collector.address, to_wei("0.08", "ether"))
    return uncapped_flatprice

