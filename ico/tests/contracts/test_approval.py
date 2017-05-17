"""Approval race condition mitigation."""
from web3.contract import Contract


def test_increase_approval(released_token: Contract, customer: str, empty_address: str, allowed_party):
    """Increase approval."""

    token = released_token
    amount = 5000
    change = 1000
    assert token.call().allowance(customer, allowed_party) == 0
    token.transact({"from": customer}).approve(allowed_party, amount)
    token.transact({"from": customer}).addApproval(allowed_party, change)
    assert token.call().allowance(customer, allowed_party) == amount + change


def test_decrease_approval(released_token: Contract, customer: str, empty_address: str, allowed_party):
    """Decrease approval."""

    token = released_token
    amount = 5000
    change = 1000
    assert token.call().allowance(customer, allowed_party) == 0
    token.transact({"from": customer}).approve(allowed_party, amount)
    token.transact({"from": customer}).subApproval(allowed_party, change)
    assert token.call().allowance(customer, allowed_party) == amount - change
