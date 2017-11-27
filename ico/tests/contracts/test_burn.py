"""Burn functionality."""

import datetime
import pytest
from ethereum.tester import TransactionFailed
from web3.contract import Contract


@pytest.fixture
def token(chain, team_multisig):
    args = [
        team_multisig,
        "Token",
        "TKN",
        1000000,
        0,
        int((datetime.datetime(2017, 4, 22, 16, 0) - datetime.datetime(1970, 1, 1)).total_seconds())
    ]
    contract, hash = chain.provider.deploy_contract('CentrallyIssuedToken', deploy_args=args)
    assert contract.call().balanceOf(team_multisig) == 1000000

    contract.transact({"from": team_multisig}).releaseTokenTransfer()
    return contract


@pytest.fixture
def token_with_customer_balance(chain, team_multisig, token, customer) -> Contract:
    """Create a Crowdsale token where transfer restrictions have been lifted."""

    # Make sure customer 1 has some token balance
    token.transact({"from": team_multisig}).transfer(customer, 10000)

    return token


def test_burn(token_with_customer_balance: Contract, customer: str):
    """Burn tokens."""

    token = token_with_customer_balance
    initial_balance = token.call().balanceOf(customer)
    initial_supply = token.call().totalSupply()
    amount = 1000

    token.transact({"from": customer}).burn(amount)

    assert token.call().balanceOf(customer) == initial_balance - amount
    assert token.call().totalSupply() == initial_supply - amount

    events = token.pastEvents("Burned").get()
    assert len(events) == 1
    e = events[-1]
    assert e["args"]["burner"] == customer
    assert e["args"]["burnedAmount"] == amount
