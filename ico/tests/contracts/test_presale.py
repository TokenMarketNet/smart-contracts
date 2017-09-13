"""Presale."""
import datetime

import pytest
from eth_utils import from_wei
from eth_utils import to_wei
from ethereum.tester import TransactionFailed
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.utils import get_constructor_arguments
from ico.state import CrowdsaleState
from ico.earlypresale import participate_early


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
    presale_crowdsale.transact({"from": team_multisig}).setFinalizeAgent(contract.address)
    assert presale_crowdsale.call().getState() == CrowdsaleState.PreFunding
    return contract


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


def test_invest_presale_move_to_crowdsale(chain, presale_fund_collector, presale_crowdsale, preico_starts_at, customer, customer_2, finalizer):
    """Move loaded funds to crowdsale."""

    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    value = to_wei(1.5, "ether")
    presale_fund_collector.transact({"from": customer_2, "value": value}).invest()

    # Crowdsale starts
    time_travel(chain, preico_starts_at)
    assert presale_crowdsale.call().finalizeAgent()
    assert presale_crowdsale.call().getState() == CrowdsaleState.Funding

    presale_fund_collector.transact().participateCrowdsaleAll()

    # Presale balances zerod
    assert presale_fund_collector.call().balances(customer) == 0
    assert presale_fund_collector.call().balances(customer_2) == 0

    # Tokens received
    assert presale_crowdsale.call().investedAmountOf(customer) == to_wei(1, "ether")
    assert presale_crowdsale.call().investedAmountOf(customer_2) == to_wei(1.5, "ether")


def test_invest_presale_move_to_crowdsale_twice(chain, presale_fund_collector, presale_crowdsale, finalizer, preico_starts_at, customer, customer_2):
    """Move loaded funds to crowdsale called twice does no harm."""

    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    value = to_wei(1.5, "ether")
    presale_fund_collector.transact({"from": customer_2, "value": value}).invest()

    time_travel(chain, preico_starts_at)
    presale_fund_collector.transact().participateCrowdsaleAll()
    presale_fund_collector.transact().participateCrowdsaleAll()

    # Tokens received
    assert presale_crowdsale.call().investedAmountOf(customer) == to_wei(1, "ether")
    assert presale_crowdsale.call().investedAmountOf(customer_2) == to_wei(1.5, "ether")


def test_invest_presale_move_to_crowdsale_too_early(chain, presale_fund_collector, presale_crowdsale, customer, customer_2, preico_starts_at):
    """Cannot loaded funds to crowdsale when crowsale is not yet open."""

    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    time_travel(chain, preico_starts_at - 1)

    with pytest.raises(TransactionFailed):
        presale_fund_collector.transact().participateCrowdsaleAll()


def test_invest_presale_move_to_crowdsale_early_whitelisted(chain, web3, presale_fund_collector, presale_crowdsale_miletstoned, customer, customer_2, preico_starts_at, team_multisig, finalizer, uncapped_token):
    """Move funds to a crowdsale that has whitelisted our contract address."""

    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    assert presale_crowdsale_miletstoned.call().getState() == CrowdsaleState.PreFunding

    # Move funds over
    updated = participate_early(chain, web3, presale_fund_collector.address, presale_crowdsale_miletstoned.address, team_multisig)
    assert updated == 1

    # The second run should not cause change
    updated = participate_early(chain, web3, presale_fund_collector.address, presale_crowdsale_miletstoned.address, team_multisig)
    assert updated == 0

    # Check that we got a special price
    expected_tokens = 1 / 0.08
    assert uncapped_token.call().balanceOf(customer) == int(expected_tokens)


def test_invest_presale_move_to_crowdsale_early_whitelisted_two(chain, web3, presale_fund_collector, presale_crowdsale_miletstoned, customer, customer_2, preico_starts_at, team_multisig, finalizer, uncapped_token):
    """Move funds to a crowdsale that has whitelisted our contract address from multiple investors."""

    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()
    presale_fund_collector.transact({"from": customer_2, "value": value}).invest()

    assert presale_crowdsale_miletstoned.call().getState() == CrowdsaleState.PreFunding

    # Move funds over
    updated = participate_early(chain, web3, presale_fund_collector.address, presale_crowdsale_miletstoned.address, team_multisig)
    assert updated == 2


def test_invest_presale_invest_too_late(chain, presale_fund_collector, presale_crowdsale, customer, customer_2, preico_starts_at, finalizer):
    """Cannot participate to presale after we have started to move funds to the actual crowdsale."""

    value = to_wei(1, "ether")
    presale_fund_collector.transact({"from": customer, "value": value}).invest()

    time_travel(chain, preico_starts_at + 1)

    presale_fund_collector.transact().participateCrowdsaleAll()

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
    sig = presale_fund_collector._prepare_transaction("invest")
    assert sig["data"] == "0xe8b5e51f"

