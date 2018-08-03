"""Releasable token."""

import pytest
from eth_tester.exceptions import TransactionFailed
from web3.contract import Contract


def test_bad_released(token: Contract, team_multisig: str, malicious_address: str, empty_address: str):
    """Only release agent can make token transferable."""

    assert not token.functions.released().call()

    with pytest.raises(TransactionFailed):
        token.functions.releaseTokenTransfer().transact({"from": malicious_address})

    # Even owner cannot release, need to go through release agent process
    with pytest.raises(TransactionFailed):
        token.functions.releaseTokenTransfer().transact({"from": team_multisig})


def test_released(released_token: Contract, customer: str, empty_address: str):
    """Released token is free to transfer."""
    token = released_token
    assert token.functions.released().call()


def test_transfer(released_token: Contract, customer: str, empty_address: str):
    """ERC-20 compatible transfer() is available."""

    token = released_token
    amount = 5000
    initial_balance = token.functions.balanceOf(customer).call()

    token.functions.transfer(empty_address, amount).transact({"from": customer})

    assert token.functions.balanceOf(customer).call() == initial_balance - amount
    assert token.functions.balanceOf(empty_address).call() == amount

    events = token.events.Transfer().createFilter(fromBlock=0).get_all_entries()
    assert len(events) == 1 + 1  # plus initial release
    e = events[-1]
    assert e["args"]["to"] == empty_address
    assert e["args"]["from"] == customer
    assert e["args"]["value"] == amount


def test_cannot_transfer(token: Contract, team_multisig, customer: str, customer_2: str):
    """Tokens cannot be transferred before they are released."""

    assert not token.call().released()

    # team_multisig is on the whitelisted transfer agent list
    assert token.functions.transferAgents(team_multisig).call() == False
    with pytest.raises(TransactionFailed):
        token.functions.transfer(customer, 10000).transact({"from": team_multisig})

    # customer cannot transfer to customer 2 before release
    assert token.functions.transferAgents(customer).call() == False
    with pytest.raises(TransactionFailed):
        token.functions.transfer(customer_2, 10000).transact({"from": customer})


def test_not_enough_balance(released_token: Contract, customer: str, empty_address: str):
    """ERC-20 transfer fails if user exceeds his/her balance."""

    token = released_token
    initial_balance = token.functions.balanceOf(customer).call()
    amount = initial_balance + 1

    with pytest.raises(TransactionFailed):
        token.functions.transfer(empty_address, amount).transact({"from": customer})


def test_transfer_with_allowance(released_token: Contract, customer: str, empty_address: str, allowed_party):
    """Tokens can be transferred with ECR-20 allowance approval."""

    token = released_token
    amount = 5000
    token.events.Approval().createFilter(fromBlock=0)
    initial_balance = token.functions.balanceOf(customer).call()
    token.functions.approve(allowed_party, amount).transact({"from": customer})
    assert token.functions.allowance(customer, allowed_party).call() == amount

    events = token.events.Approval().createFilter(fromBlock=0).get_all_entries()
    assert len(events) > 0  # Edgeless gets 2 events, because one is needed to construct token
    e = events[-1]
    assert e["args"]["owner"] == customer
    assert e["args"]["spender"] == allowed_party
    assert e["args"]["value"] == amount

    token.transact({"from": allowed_party}).transferFrom(customer, empty_address, amount)

    events = token.events.Transfer().createFilter(fromBlock=0).get_all_entries()
    assert len(events) == 1 + 1
    e = events[-1]
    assert e["args"]["to"] == empty_address
    assert e["args"]["from"] == customer
    assert e["args"]["value"] == amount

    assert token.functions.balanceOf(customer).call() == initial_balance - amount
    assert token.functions.balanceOf(empty_address).call() == amount
    assert token.functions.allowance(customer, allowed_party).call() == 0


def test_transfer_with_allowance_exceeded(released_token: Contract, customer: str, empty_address: str, allowed_party):
    """One cannot transfers more than approved allowance."""

    token = released_token
    amount = 5000
    token.functions.approve(allowed_party, amount).transact({"from": customer})

    with pytest.raises(TransactionFailed):
        token.functions.transferFrom(customer, empty_address, amount+1).transact({"from": allowed_party})

