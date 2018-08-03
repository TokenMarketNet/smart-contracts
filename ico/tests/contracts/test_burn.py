"""Burn functionality."""

import datetime
import pytest
# from ethereum.tester import TransactionFailed
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
    assert contract.functions.balanceOf(team_multisig).call() == 1000000

    contract.functions.releaseTokenTransfer().transact({"from": team_multisig})
    return contract


@pytest.fixture
def token_with_customer_balance(chain, team_multisig, token, customer) -> Contract:
    """Create a Crowdsale token where transfer restrictions have been lifted."""

    # Make sure customer 1 has some token balance
    token.functions.transfer(customer, 10000).transact({"from": team_multisig})

    return token


def test_burn(token_with_customer_balance: Contract, customer: str):
    """Burn tokens."""

    token = token_with_customer_balance
    initial_balance = token.functions.balanceOf(customer).call()
    initial_supply = token.functions.totalSupply().call()
    amount = 1000
    event_filter = token.events.Burned().createFilter(fromBlock=0)
    token.functions.burn(amount).transact({"from": customer})

    assert token.functions.balanceOf(customer).call() == initial_balance - amount
    assert token.functions.totalSupply().call() == initial_supply - amount
    events = event_filter.get_all_entries()
    assert len(events) == 1
    e = events[-1]
    assert e["args"]["burner"] == customer
    assert e["args"]["burnedAmount"] == amount
