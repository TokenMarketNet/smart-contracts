"""Finalize crowdsale."""
import pytest
from eth_utils import to_wei
from ethereum.tester import TransactionFailed
from web3 import Web3

from populus.chain import TestRPCChain
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.tests.utils import CrowdsaleState


def test_finalize_fail_goal(chain: TestRPCChain, uncapped_flatprice_final: Contract, customer: str, preico_starts_at, preico_ends_at, preico_funding_goal):
    """Finalize can be done only for successful crowdsales."""

    time_travel(chain, preico_starts_at + 1)
    wei_value = preico_funding_goal // 2

    uncapped_flatprice_final.transact({"from": customer, "value": wei_value}).buy()

    time_travel(chain, preico_ends_at + 1)
    assert uncapped_flatprice_final.call().getState() == CrowdsaleState.Failure

    with pytest.raises(TransactionFailed):
        uncapped_flatprice_final.transact().finalize()


def test_finalize_success(chain: TestRPCChain, uncapped_flatprice_final: Contract, uncapped_token: Contract, customer: str, preico_starts_at, preico_ends_at, preico_funding_goal, default_finalize_agent):
    """Finalize releases the token."""

    time_travel(chain, preico_starts_at + 1)
    wei_value = preico_funding_goal

    uncapped_flatprice_final.transact({"from": customer, "value": wei_value}).buy()

    time_travel(chain, preico_ends_at + 1)
    assert uncapped_flatprice_final.call().getState() == CrowdsaleState.Success
    assert uncapped_flatprice_final.call().finalizeAgent() == default_finalize_agent.address

    # Release the tokens
    uncapped_flatprice_final.transact().finalize()
    assert uncapped_flatprice_final.call().getState() == CrowdsaleState.Finalized

    # Here we go
    assert uncapped_token.call().released()
    assert uncapped_token.call().mintingFinished()


def test_finalize_fail_again(chain: TestRPCChain, uncapped_flatprice_final: Contract, customer: str, preico_starts_at, preico_ends_at, preico_funding_goal):
    """Finalize cannot be done again."""

    time_travel(chain, preico_starts_at + 1)
    wei_value = preico_funding_goal

    uncapped_flatprice_final.transact({"from": customer, "value": wei_value}).buy()

    time_travel(chain, preico_ends_at + 1)
    assert uncapped_flatprice_final.call().getState() == CrowdsaleState.Success

    uncapped_flatprice_final.transact().finalize()
    with pytest.raises(TransactionFailed):
        uncapped_flatprice_final.transact().finalize()


def test_finalize_only_by_crowdsale(chain: TestRPCChain, uncapped_flatprice_final: Contract, team_multisig: str, customer: str, preico_starts_at, preico_ends_at, preico_funding_goal, default_finalize_agent):
    """Finalizer can be only triggered by crowdsale."""

    time_travel(chain, preico_starts_at + 1)
    wei_value = preico_funding_goal

    uncapped_flatprice_final.transact({"from": customer, "value": wei_value}).buy()

    time_travel(chain, preico_ends_at + 1)
    assert uncapped_flatprice_final.call().getState() == CrowdsaleState.Success

    # Checks for the owner
    with pytest.raises(TransactionFailed):
        default_finalize_agent.transact({"from": team_multisig}).finalizeCrowdsale()

