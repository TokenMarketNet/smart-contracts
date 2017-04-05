"""Refund."""

import pytest
from decimal import Decimal
from eth_utils import from_wei
from eth_utils import to_wei
from ethereum.tester import TransactionFailed
from web3 import Web3

from populus.chain import TestRPCChain
from web3.contract import Contract

from ico.state import CrowdsaleState
from ico.tests.utils import time_travel


#: Max ether we assume will be lost in transaction fees when getting funds back
TRANSACTION_COST_ETH_EPSILON = Decimal(0.01)


@pytest.fixture
def failed_ico(chain: TestRPCChain, web3, uncapped_flatprice: Contract, team_multisig, customer, customer_2, preico_starts_at, preico_ends_at, uncapped_flatprice_finalizer) -> Contract:
    """An ICO that did not reach a goal, but has participants.

    Both ``customer`` and ``customer_2`` had bought token.

    * customer: 50 ether
    * customer_2: 70 ether
    * total: 120 ether
    * minimum funding goal: 1200 ether

    """

    time_travel(chain, preico_starts_at + 1)

    uncapped_flatprice.transact({"from": customer, "value": to_wei(50, "ether")}).buy()
    uncapped_flatprice.transact({"from": customer_2, "value": to_wei(70, "ether")}).buy()

    # Make sure customer 1 has some token balance
    time_travel(chain, preico_ends_at + 1)
    return uncapped_flatprice


@pytest.fixture
def failed_ico_ready_to_refund(chain: TestRPCChain, failed_ico: Contract, team_multisig) -> Contract:
    """An ICO that did not reach a goal, but has participants.

    The team has moved funds back from the multisig wallet on the crowdsale contract. Note that due to transaction fees you need to pay a minimal transaction cost out of your own pocket.
    """
    failed_ico.transact({"from" : team_multisig, "value": failed_ico.call().weiRaised()}).loadRefund()
    return failed_ico


def test_can_begin_refund(failed_ico, web3: Web3, team_multisig):
    """After a failure the contract is ready to load refunds."""

    assert failed_ico.call().getState() == CrowdsaleState.Failure
    assert failed_ico.call().weiRaised() == to_wei(120, "ether")
    assert web3.eth.getBalance(failed_ico.address) == 0


def test_too_small_refund(failed_ico, web3: Web3, team_multisig, customer):
    """All refund must be loaded before the refund can begin."""

    assert failed_ico.call().getState() == CrowdsaleState.Failure
    failed_ico.transact({"from": team_multisig, "value": failed_ico.call().weiRaised() // 2}).loadRefund()
    assert failed_ico.call().getState() == CrowdsaleState.Failure

    # Customer tries to reclaim refunds early
    with pytest.raises(TransactionFailed):
        failed_ico.transact({"from": customer}).refund()


def test_refund(failed_ico_ready_to_refund: Contract, web3: Web3, customer: str, customer_2: str):
    """Customers can claim their refunds."""

    assert failed_ico_ready_to_refund.call().loadedRefund() == to_wei(120, "ether")
    assert failed_ico_ready_to_refund.call().getState() == CrowdsaleState.Refunding

    # Check that the customer gets money back
    invested_amount = failed_ico_ready_to_refund.call().investedAmountOf(customer)
    begin_balance = web3.eth.getBalance(customer)
    failed_ico_ready_to_refund.transact({"from": customer}).refund()
    end_balance = web3.eth.getBalance(customer)

    eth = from_wei(end_balance - begin_balance, "ether")  # Decimal('49.999999999999954693')
    assert (end_balance - begin_balance) >= eth - TRANSACTION_COST_ETH_EPSILON

    failed_ico_ready_to_refund.transact({"from": customer_2}).refund()

    # Everything has been refunded
    assert failed_ico_ready_to_refund.call().weiRefunded() == to_wei(120, "ether")


def test_cannot_refund_twice(failed_ico_ready_to_refund: Contract, customer: str):
    """Customer can reclaim refund only once."""

    assert failed_ico_ready_to_refund.call().getState() == CrowdsaleState.Refunding

    failed_ico_ready_to_refund.transact({"from": customer}).refund()
    with pytest.raises(TransactionFailed):
        failed_ico_ready_to_refund.transact({"from": customer}).refund()


