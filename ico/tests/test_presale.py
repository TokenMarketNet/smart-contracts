"""Presale."""
import datetime

import pytest
from eth_utils import from_wei
from eth_utils import to_wei
from ethereum.tester import TransactionFailed
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.utils import get_constructor_arguments


@pytest.fixture
def presale_freeze_ends_at() -> int:
    """How long presale funds stay frozen until refund."""
    return int(datetime.datetime(2017, 1, 1).timestamp())


@pytest.fixture
def presale_fund_collector(chain, presale_freeze_ends_at, team_multisig) -> Contract:
    """In actual ICO, the price is doubled (for testing purposes)."""
    args = [
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


def test_invest_presale(presale_fund_collector, customer, presale_freeze_ends_at):
    """Customer can invest into a presale."""
    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    assert presale_fund_collector.call().investorCount() == 1
    assert presale_fund_collector.call().investors(0) == customer
    assert presale_fund_collector.call().balances(customer) == to_wei(1, "ether")

    assert presale_fund_collector.call().freezeEndsAt() == presale_freeze_ends_at


def test_invest_presale_minimum_limit(presale_fund_collector, customer):
    """Invested rejectd under minimum buy in."""

    value = to_wei(0.5, "ether")
    with pytest.raises(TransactionFailed):
        presale_fund_collector.transact({"from": customer, "value": value}).invest()


def test_invest_presale_twice(presale_fund_collector, customer):
    """Same investor can buy in twice"""
    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    value = to_wei(1.5, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    assert presale_fund_collector.call().investorCount() == 1
    assert presale_fund_collector.call().investors(0) == customer
    assert presale_fund_collector.call().balances(customer) == to_wei(2.5, "ether")


def test_invest_presale_two_parties(presale_fund_collector, customer, customer_2):
    """Two different investors can participate"""
    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    value = to_wei(1.5, "ether")
    presale_fund_collector.transact({"from": customer_2, "value": value}).invest()

    assert presale_fund_collector.call().investorCount() == 2
    assert presale_fund_collector.call().investors(0) == customer
    assert presale_fund_collector.call().investors(1) == customer_2

    assert presale_fund_collector.call().balances(customer) == to_wei(1, "ether")
    assert presale_fund_collector.call().balances(customer_2) == to_wei(1.5, "ether")



def test_invest_presale_move_to_crowdsale(chain, presale_fund_collector, presale_crowdsale, preico_starts_at, customer, customer_2):
    """Move loaded funds to crowdsale."""

    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    value = to_wei(1.5, "ether")
    presale_fund_collector.transact({"from": customer_2, "value": value}).invest()

    time_travel(chain, preico_starts_at)
    presale_fund_collector.transact().parcipateCrowdsaleAll()

    # Presale balances zerod
    presale_fund_collector.call().balances(customer) == 0
    presale_fund_collector.call().balances(customer_2) == 0

    # Tokens received
    presale_crowdsale.call().investedAmountOf(customer) == to_wei(1, "ether")
    presale_crowdsale.call().investedAmountOf(customer_2) == to_wei(1.5, "ether")


def test_invest_presale_move_to_crowdsale_twice(chain, presale_fund_collector, presale_crowdsale, preico_starts_at, customer, customer_2):
    """Move loaded funds to crowdsale called twice does no harm."""

    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    value = to_wei(1.5, "ether")
    presale_fund_collector.transact({"from": customer_2, "value": value}).invest()

    time_travel(chain, preico_starts_at)
    presale_fund_collector.transact().parcipateCrowdsaleAll()
    presale_fund_collector.transact().parcipateCrowdsaleAll()

    # Tokens received
    presale_crowdsale.call().investedAmountOf(customer) == to_wei(1, "ether")
    presale_crowdsale.call().investedAmountOf(customer_2) == to_wei(1.5, "ether")


def test_invest_presale_move_to_crowdsale_too_early(chain, presale_fund_collector, presale_crowdsale, customer, customer_2, preico_starts_at):
    """Cannot loaded funds to crowdsale when crowsale is not yet open."""

    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    time_travel(chain, preico_starts_at - 1)

    with pytest.raises(TransactionFailed):
        presale_fund_collector.transact().parcipateCrowdsaleAll()


def test_invest_presale_invest_too_late(chain, presale_fund_collector, presale_crowdsale, customer, customer_2, preico_starts_at):
    """Cannot participate to presale after we have started to move funds to the actual crowdsale."""

    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    time_travel(chain, preico_starts_at + 1)

    presale_fund_collector.transact().parcipateCrowdsaleAll()

    # No more presales
    with pytest.raises(TransactionFailed):
        presale_fund_collector.transact({"from": customer, "value": value}).invest()


def test_invest_presale_refund(chain, web3, presale_fund_collector, presale_crowdsale, preico_starts_at, customer, customer_2):
    """We can refund"""

    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    value = to_wei(1.5, "ether")
    presale_fund_collector.transact({"from": customer_2, "value": value}).invest()

    time_travel(chain, presale_fund_collector.call().freezeEndsAt() + 1)

    before_refund = web3.eth.getBalance(customer)
    presale_fund_collector.transact({"from": customer}).refund()
    after_refund = web3.eth.getBalance(customer)

    assert from_wei(after_refund - before_refund, "ether") > 0.99  # gas cost epsilon
    assert presale_fund_collector.call().balances(customer) == 0


def test_invest_presale_refund_early(chain, web3, presale_fund_collector, presale_crowdsale, preico_starts_at, customer, customer_2):
    """There are no early refunds"""

    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    time_travel(chain, presale_fund_collector.call().freezeEndsAt() - 1)

    with pytest.raises(TransactionFailed):
        presale_fund_collector.transact({"from": customer}).refund()


def test_invest_presale_refund_extra(chain, web3, presale_fund_collector, presale_crowdsale, preico_starts_at, customer, customer_2):
    """Refund is given only once"""

    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    value = to_wei(1.5, "ether")
    presale_fund_collector.transact({"from": customer_2, "value": value}).invest()

    time_travel(chain, presale_fund_collector.call().freezeEndsAt() + 1)

    presale_fund_collector.transact({"from": customer}).refund()
    with pytest.raises(TransactionFailed):
        presale_fund_collector.transact({"from": customer}).refund()


def test_only_owner_sets_crowdsale(chain, presale_fund_collector, uncapped_flatprice, customer):
    """Only owner can set the crowdsale for presale."""

    with pytest.raises(TransactionFailed):
        presale_fund_collector.transact({"from": customer}).setCrowdsale(uncapped_flatprice.address)


def test_estimate_invest_cost(chain, web3, presale_fund_collector, presale_crowdsale, preico_starts_at, customer, customer_2):
    """Estimate invest gas cost."""

    value = to_wei(1, "ether")
    transaction = {"from": customer, "value": value}
    cost = presale_fund_collector.estimateGas(transaction=transaction).invest()  # 107459
    assert cost > 0
    assert cost < 200000


def test_invest_signature(chain, web3, presale_fund_collector, presale_crowdsale, preico_starts_at, customer, customer_2):
    """Check we get invest() signature for data payload."""

    value = to_wei(1, "ether")
    transaction = {"from": customer, "value": value}
    sig = presale_fund_collector._prepare_transaction("invest")
    assert sig["data"] == "0xe8b5e51f"


def test_encode_constructor(chain, web3, presale_fund_collector, presale_freeze_ends_at):
    """Needed for getting Etherscan.io signature in presale.py."""

    args = [
        int(1),
        to_wei(1, "ether")
    ]
    data = get_constructor_arguments(presale_fund_collector, args)
    assert data == "00000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000de0b6b3a7640000"
