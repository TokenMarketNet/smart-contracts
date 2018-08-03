"""Test AML reclaim script core."""
from io import StringIO

import pytest
from web3.contract import Contract

from ico.amlreclaim import prepare_csv, count_tokens_to_reclaim, reclaim_all


CSV_SOURCE = """address,label
{}, customer
"""


@pytest.fixture
def aml_reclaim_setup(aml_token: Contract, team_multisig: str, customer: str, customer_2):
    """Setup some tokens for accounts for performing the reclaim test. ."""

    aml_token.functions.setTransferAgent(team_multisig, True).transact({"from": team_multisig})
    aml_token.functions.transfer(customer, 1000000).transact({"from": team_multisig})
    aml_token.functions.transfer(customer_2, 2000000).transact({"from": team_multisig})


@pytest.fixture
def csv_stream(aml_reclaim_setup, customer):
    """Set up a CSV file for reclaim"""

    source = CSV_SOURCE.format(customer)
    return StringIO(source)


def test_count_reclaim(csv_stream, customer, aml_token: Contract, team_multisig):
    """Count how many tokens we have to reclaim."""

    rows = prepare_csv(csv_stream, "address", "label")
    total = count_tokens_to_reclaim(aml_token, rows)
    assert total == 1000000


def test_reclaim_csv(csv_stream, customer, customer_2, aml_token: Contract, team_multisig):
    """Tokens are reclaimed correctly from CSV input.."""

    start_owner_balance = aml_token.functions.balanceOf(team_multisig).call()
    rows = prepare_csv(csv_stream, "address", "label")
    performed_op_count = reclaim_all(aml_token, rows, {"from": team_multisig})
    assert performed_op_count == 1

    assert aml_token.functions.balanceOf(customer).call() == 0
    assert aml_token.functions.balanceOf(customer_2).call() == 2000000
    assert aml_token.functions.balanceOf(team_multisig).call() == start_owner_balance + 1000000


def test_reclaim_twice(csv_stream, customer, aml_token: Contract, team_multisig):
    """If we have tokens alreadhy reclaimed in the input, entries are skipped."""

    rows = prepare_csv(csv_stream, "address", "label")

    # First run
    performed_op_count = reclaim_all(aml_token, rows, {"from": team_multisig})
    assert performed_op_count == 1

    # Attempt to continue
    performed_op_count = reclaim_all(aml_token, rows, {"from": team_multisig})
    assert performed_op_count == 0

