"""Uncapped ICO."""

import pytest
from eth_utils import to_wei
from ethereum.tester import TransactionFailed
from web3 import Web3

from populus.chain import TestRPCChain
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.state import CrowdsaleState


def test_initialized(uncapped_flatprice: Contract, uncapped_token: Contract, team_multisig, preico_starts_at, preico_ends_at, preico_funding_goal):
    """Is initialized with the parameters we want."""

    # We have owner
    assert uncapped_flatprice.call().owner() == team_multisig

    # Crowdsale contract is in minters
    assert uncapped_token.call().mintAgents(uncapped_flatprice.address) == True
    assert not uncapped_token.call().released()
    assert not uncapped_flatprice.call().halted()
    assert uncapped_flatprice.call().startsAt() == preico_starts_at
    assert uncapped_flatprice.call().endsAt() == preico_ends_at
    assert uncapped_flatprice.call().getState() == CrowdsaleState.PreFunding
    assert uncapped_flatprice.call().minimumFundingGoal() == preico_funding_goal


def test_buy_early(chain: TestRPCChain, uncapped_flatprice: Contract, customer: str, preico_starts_at):
    """Cannot buy too early."""

    time_travel(chain, preico_starts_at - 1)
    assert uncapped_flatprice.call().getState() == CrowdsaleState.PreFunding
    with pytest.raises(TransactionFailed):
        uncapped_flatprice.transact({"from": customer, "value": to_wei(1, "ether")}).buy()


def test_buy(chain: TestRPCChain, web3: Web3, uncapped_flatprice: Contract, uncapped_token: Contract, customer: str, preico_token_price, preico_starts_at, team_multisig):
    """Can buy when crowdsale is running."""

    original_balance = web3.eth.getBalance(team_multisig)
    wei_value = to_wei(1, "ether")
    buys_tokens = wei_value // preico_token_price
    assert buys_tokens > 0

    time_travel(chain, preico_starts_at + 1)
    assert uncapped_flatprice.call().getState() == CrowdsaleState.Funding

    uncapped_flatprice.transact({"from": customer, "value": wei_value}).buy()

    #
    # See everything was correctly credited
    #

    # Tokens on every account
    uncapped_token.call().balanceOf(customer) == buys_tokens
    uncapped_token.call().totalSupply() == buys_tokens
    uncapped_flatprice.call().tokensSold() == buys_tokens

    # Ether on every account
    uncapped_flatprice.call().weiRaised() == wei_value
    uncapped_flatprice.call().investedAmountOf(customer) == wei_value
    balance_diff = web3.eth.getBalance(team_multisig) - original_balance
    assert balance_diff == wei_value

    # Investors
    uncapped_flatprice.call().investorCount() == 1

    #
    # Events
    #

    # Crowdsale
    events = uncapped_flatprice.pastEvents("Invested").get()
    assert len(events) == 1
    e = events[0]
    assert e["args"]["investor"] == customer
    assert e["args"]["weiAmount"] == wei_value
    assert e["args"]["tokenAmount"] == buys_tokens

    # ERC-20
    events = uncapped_token.pastEvents("Transfer").get()
    assert len(events) == 1
    e = events[0]
    assert e["args"]["from"] == "0x0000000000000000000000000000000000000000"
    assert e["args"]["to"] == customer
    assert e["args"]["value"] == buys_tokens


def test_buy_again(chain: TestRPCChain, web3: Web3, uncapped_flatprice: Contract, uncapped_token: Contract, customer: str, preico_token_price, preico_starts_at, team_multisig):
    """Can buy more."""

    original_balance = web3.eth.getBalance(team_multisig)
    wei_value = to_wei(1, "ether")
    buys_tokens = wei_value // preico_token_price
    assert buys_tokens > 0

    time_travel(chain, preico_starts_at + 1)

    # Buy twice
    uncapped_flatprice.transact({"from": customer, "value": wei_value}).buy()
    uncapped_flatprice.transact({"from": customer, "value": wei_value}).buy()

    #
    # See everything was correctly credited
    #

    # Tokens on every account
    uncapped_token.call().balanceOf(customer) == buys_tokens * 2
    uncapped_token.call().totalSupply() == buys_tokens * 2
    uncapped_flatprice.call().tokensSold() == buys_tokens * 2

    # Ether on every account
    uncapped_flatprice.call().weiRaised() == wei_value * 2
    uncapped_flatprice.call().investedAmountOf(customer) == wei_value * 2
    balance_diff = web3.eth.getBalance(team_multisig) - original_balance
    assert balance_diff == wei_value * 2

    # Investors
    uncapped_flatprice.call().investorCount() == 1

    #
    # Events
    #

    # Crowdsale
    events = uncapped_flatprice.pastEvents("Invested").get()
    assert len(events) == 2

    # ERC-20
    events = uncapped_token.pastEvents("Transfer").get()
    assert len(events) == 2


def test_buy_two_investors(chain: TestRPCChain, web3: Web3, uncapped_flatprice: Contract, uncapped_token: Contract, customer: str, customer_2, preico_token_price, preico_starts_at, team_multisig):
    """Two different customers buy in."""

    original_balance = web3.eth.getBalance(team_multisig)
    wei_value = to_wei(1, "ether")
    buys_tokens = wei_value // preico_token_price
    assert buys_tokens > 0

    time_travel(chain, preico_starts_at + 1)

    # Buy twice
    uncapped_flatprice.transact({"from": customer, "value": wei_value}).buy()
    uncapped_flatprice.transact({"from": customer_2, "value": wei_value}).buy()

    #
    # See everything was correctly credited
    #

    # Tokens on every account
    uncapped_token.call().balanceOf(customer) == buys_tokens
    uncapped_token.call().totalSupply() == buys_tokens * 2
    uncapped_flatprice.call().tokensSold() == buys_tokens * 2

    # Ether on every account
    uncapped_flatprice.call().weiRaised() == wei_value * 2
    uncapped_flatprice.call().investedAmountOf(customer) == wei_value
    balance_diff = web3.eth.getBalance(team_multisig) - original_balance
    assert balance_diff == wei_value * 2

    # Investors
    uncapped_flatprice.call().investorCount() == 2

    #
    # Events
    #

    # Crowdsale
    events = uncapped_flatprice.pastEvents("Invested").get()
    assert len(events) == 2

    # ERC-20
    events = uncapped_token.pastEvents("Transfer").get()
    assert len(events) == 2


def test_buy_reach_goal(chain: TestRPCChain, flat_pricing, uncapped_flatprice: Contract, customer: str, preico_starts_at, preico_ends_at, preico_funding_goal):
    """Goal can be reached with a sufficient investment."""

    time_travel(chain, preico_starts_at + 1)
    wei_value = preico_funding_goal

    # Check that we don't have issues with our pricing
    assert flat_pricing.call().calculatePrice(wei_value, 0, 0, customer) > 0

    uncapped_flatprice.transact({"from": customer, "value": wei_value}).buy()

    # We got investment event
    events = uncapped_flatprice.pastEvents("Invested").get()
    assert len(events) == 1
    e = events[0]
    assert e["args"]["investor"] == customer
    assert e["args"]["weiAmount"] == wei_value

    assert uncapped_flatprice.call().weiRaised() == wei_value
    assert uncapped_flatprice.call().weiRaised() == uncapped_flatprice.call().minimumFundingGoal()
    assert uncapped_flatprice.call().isMinimumGoalReached()

    time_travel(chain, preico_ends_at + 1)
    assert uncapped_flatprice.call().getState() == CrowdsaleState.Success


def test_buy_fail_goal(chain: TestRPCChain, uncapped_flatprice: Contract, customer: str, preico_starts_at, preico_ends_at, preico_funding_goal):
    """Goal is not reached if there is not enough investment."""

    time_travel(chain, preico_starts_at + 1)
    wei_value = preico_funding_goal // 2

    uncapped_flatprice.transact({"from": customer, "value": wei_value}).buy()

    time_travel(chain, preico_ends_at + 1)
    assert uncapped_flatprice.call().getState() == CrowdsaleState.Failure


def test_buy_late_goal_not_reached(chain: TestRPCChain, uncapped_flatprice: Contract, customer: str, preico_ends_at):
    """Cannot buy after closing time when the goal was not reached."""

    time_travel(chain, preico_ends_at + 1)
    assert uncapped_flatprice.call().getState() == CrowdsaleState.Failure
    with pytest.raises(TransactionFailed):
        uncapped_flatprice.transact({"from": customer, "value": to_wei(1, "ether")}).buy()


def test_buy_late_goal_reached(chain: TestRPCChain, uncapped_flatprice_goal_reached: Contract, customer: str, preico_ends_at):
    """Cannot buy after closing time when the goal was not reached."""

    time_travel(chain, preico_ends_at + 1)
    assert uncapped_flatprice_goal_reached.call().getState() == CrowdsaleState.Success
    with pytest.raises(TransactionFailed):
        uncapped_flatprice_goal_reached.transact({"from": customer, "value": to_wei(1, "ether")}).buy()


def test_buy_dust(chain: TestRPCChain, web3: Web3, uncapped_flatprice: Contract, uncapped_token: Contract, customer: str, preico_token_price, preico_starts_at, team_multisig):
    """Cannot buy with too small transaction."""

    wei_value = 1

    time_travel(chain, preico_starts_at + 1)

    with pytest.raises(TransactionFailed):
        uncapped_flatprice.transact({"from": customer, "value": wei_value}).buy()


def test_deposit_default_payabl(chain: TestRPCChain, web3: Web3, uncapped_flatprice: Contract, uncapped_token: Contract, customer: str, preico_token_price, preico_starts_at, team_multisig):
    """Cannot just send money to the contract address and expect getting tokens.."""

    wei_value = to_wei(100, "ether")
    time_travel(chain, preico_starts_at + 1)
    with pytest.raises(TransactionFailed):
        web3.eth.sendTransaction({"from": customer, "value": wei_value, "to": uncapped_flatprice.address})


def test_cannot_mint(chain: TestRPCChain, web3: Web3, uncapped_flatprice: Contract, uncapped_token: Contract, customer: str, preico_token_price, preico_starts_at, team_multisig):
    """Only crowdsale contract can mint new tokens."""

    time_travel(chain, preico_starts_at + 1)

    with pytest.raises(TransactionFailed):
        uncapped_token.transact({"from": customer}).mint(customer, 1000)


def test_halt(chain: TestRPCChain, web3: Web3, uncapped_flatprice: Contract, uncapped_token: Contract, customer: str, preico_token_price, preico_starts_at, team_multisig):
    """Cannot buy tokens during the emergency pause mode."""

    time_travel(chain, preico_starts_at + 1)
    wei_value = to_wei(1, "ether")

    uncapped_flatprice.transact({"from": team_multisig}).halt()
    assert uncapped_flatprice.call().halted()

    with pytest.raises(TransactionFailed):
        uncapped_flatprice.transact({"from": customer, "value": wei_value}).buy()

    uncapped_flatprice.transact({"from": team_multisig}).unhalt()
    assert not uncapped_flatprice.call().halted()
    uncapped_flatprice.transact({"from": customer, "value": wei_value}).buy()


def test_malicious_halt(chain: TestRPCChain, web3: Web3, uncapped_flatprice: Contract, uncapped_token: Contract, malicious_address: str):
    """Only owner can pause."""

    with pytest.raises(TransactionFailed):
        uncapped_flatprice.transact({"from": malicious_address}).halt()


def test_finalize(chain: TestRPCChain, web3: Web3, uncapped_flatprice: Contract, malicious_address: str):
    """Crowdsale can be finalized and the tokens can be released."""

    with pytest.raises(TransactionFailed):
        uncapped_flatprice.transact({"from": malicious_address}).halt()
