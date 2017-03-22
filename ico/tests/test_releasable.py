"""Releasable token."""
"""Releasable token."""

import pytest
from ethereum.tester import TransactionFailed
from web3.contract import Contract


def test_bad_released(token: Contract, team_multisig: str, malicious_address: str, empty_address: str):
    """Only release agent can make token transferable."""

    assert not token.call().released()

    with pytest.raises(TransactionFailed):
        token.transact({"from": malicious_address}).releaseTokenTransfer()

    # Even owner cannot release, need to go through release agent process
    with pytest.raises(TransactionFailed):
        token.transact({"from": team_multisig}).releaseTokenTransfer()


def test_released(released_token: Contract, customer: str, empty_address: str):
    """Released token is free to transfer."""
    token = released_token
    assert token.call().released()


def test_transfer(released_token: Contract, customer: str, empty_address: str):
    """ERC-20 compatible transfer() is available."""

    token = released_token
    amount = 5000
    initial_balance = token.call().balanceOf(customer)

    token.transact({"from": customer}).transfer(empty_address, amount)

    assert token.call().balanceOf(customer) == initial_balance - amount
    assert token.call().balanceOf(empty_address) == amount

    events = token.pastEvents("Transfer").get()
    assert len(events) == 1 + 1  # plus initial release
    e = events[-1]
    assert e["args"]["to"] == empty_address
    assert e["args"]["from"] == customer
    assert e["args"]["value"] == amount


def test_cannot_transfer(token: Contract, team_multisig, customer: str, customer_2: str):
    """Tokens cannot be transferred before they are released."""

    assert not token.call().released()

    # team_multisig is on the whitelisted transfer agent list
    assert token.call().transferAgents(team_multisig) == False
    with pytest.raises(TransactionFailed):
        token.transact({"from": team_multisig}).transfer(customer, 10000)

    # customer cannot transfer to customer 2 before release
    assert token.call().transferAgents(customer) == False
    with pytest.raises(TransactionFailed):
        token.transact({"from": customer}).transfer(customer_2, 10000)


def test_not_enough_balance(released_token: Contract, customer: str, empty_address: str):
    """ERC-20 transfer fails if user exceeds his/her balance."""

    token = released_token
    initial_balance = token.call().balanceOf(customer)
    amount = initial_balance + 1

    with pytest.raises(TransactionFailed):
        token.transact({"from": customer}).transfer(empty_address, amount)


def test_transfer_with_allowance(released_token: Contract, customer: str, empty_address: str, allowed_party):
    """Tokens can be transferred with ECR-20 allowance approval."""

    token = released_token
    amount = 5000
    initial_balance = token.call().balanceOf(customer)
    token.transact({"from": customer}).approve(allowed_party, amount)
    assert token.call().allowance(customer, allowed_party) == amount

    events = token.pastEvents("Approval").get()
    assert len(events) > 0  # Edgeless gets 2 events, because one is needed to construct token
    e = events[-1]
    assert e["args"]["owner"] == customer
    assert e["args"]["spender"] == allowed_party
    assert e["args"]["value"] == amount

    token.transact({"from": allowed_party}).transferFrom(customer, empty_address, amount)

    events = token.pastEvents("Transfer").get()
    assert len(events) == 1 + 1  # plus initial transfer
    e = events[-1]
    assert e["args"]["to"] == empty_address
    assert e["args"]["from"] == customer
    assert e["args"]["value"] == amount

    assert token.call().balanceOf(customer) == initial_balance - amount
    assert token.call().balanceOf(empty_address) == amount
    assert token.call().allowance(customer, allowed_party) == 0


def test_transfer_with_allowance_exceeded(released_token: Contract, customer: str, empty_address: str, allowed_party):
    """One cannot transfers more than approved allowance."""

    token = released_token
    amount = 5000
    token.transact({"from": customer}).approve(allowed_party, amount)

    with pytest.raises(TransactionFailed):
        token.transact({"from": allowed_party}).transferFrom(customer, empty_address, amount+1)
