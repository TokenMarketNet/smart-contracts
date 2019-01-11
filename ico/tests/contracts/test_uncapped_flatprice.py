"""Uncapped ICO."""

import pytest
from eth_utils import to_wei
from eth_tester.exceptions import TransactionFailed
from web3 import Web3

from populus.chain import TesterChain
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.state import CrowdsaleState


@pytest.fixture
def ico(uncapped_flatprice, uncapped_flatprice_finalizer):
    """Set up a crowdsale for this test module with finalizer in place."""
    return uncapped_flatprice


def test_initialized(ico: Contract, uncapped_token: Contract, team_multisig, preico_starts_at, preico_ends_at, preico_funding_goal):
    """Is initialized with the parameters we want."""

    # We have owner
    assert ico.functions.owner().call() == team_multisig

    # Crowdsale contract is in minters
    assert uncapped_token.functions.mintAgents(ico.address).call() == True
    assert not uncapped_token.functions.released().call()
    assert not ico.functions.halted().call()
    assert ico.functions.startsAt().call() == preico_starts_at
    assert ico.functions.endsAt().call() == preico_ends_at
    assert ico.functions.getState().call() == CrowdsaleState.PreFunding
    assert ico.functions.minimumFundingGoal().call() == preico_funding_goal


def test_buy_early(chain: TesterChain, ico: Contract, customer: str, preico_starts_at, uncapped_token):
    """Cannot buy too early."""
    # two seconds early
    time_travel(chain, preico_starts_at - 2)
    assert ico.functions.getState().call() == CrowdsaleState.PreFunding
    with pytest.raises(TransactionFailed):
        ico.functions.buy().transact({"from": customer, "value": to_wei(1, "ether")})


def test_buy_early_whitelisted(chain: TesterChain, ico: Contract, customer: str, preico_starts_at, team_multisig, uncapped_token):
    """Whitelisted participants can buy earliy."""

    time_travel(chain, preico_starts_at - 1)
    assert ico.functions.getState().call() == CrowdsaleState.PreFunding
    ico.functions.setEarlyParicipantWhitelist(customer, True).transact({"from": team_multisig})
    ico.functions.buy().transact({"from": customer, "value": to_wei(1, "ether")})
    assert uncapped_token.functions.balanceOf(customer).call() > 0


def test_early_whitelist_only_owner(chain: TesterChain, ico: Contract, customer: str, preico_starts_at, team_multisig, uncapped_token):
    """Only owner can early whitelist."""

    time_travel(chain, preico_starts_at - 1)
    assert ico.functions.getState().call() == CrowdsaleState.PreFunding
    with pytest.raises(TransactionFailed):
        ico.functions.setEarlyParicipantWhitelist(customer, True).transact({"from": customer})


def test_buy_one_investor(chain: TesterChain, web3: Web3, ico: Contract, uncapped_token: Contract, customer: str, preico_token_price, preico_starts_at, team_multisig):
    """Can buy when crowdsale is running."""

    original_balance = web3.eth.getBalance(team_multisig)
    wei_value = to_wei(1, "ether")
    buys_tokens = wei_value // preico_token_price
    assert buys_tokens > 0

    time_travel(chain, preico_starts_at + 1)
    assert ico.functions.getState().call() == CrowdsaleState.Funding
    assert ico.functions.investorCount().call() == 0
    assert ico.functions.investedAmountOf(customer).call() == 0
    ico.functions.buy().transact({"from": customer, "value": wei_value})

    #
    # See everything was correctly credited
    #

    # Tokens on every account
    assert uncapped_token.functions.balanceOf(customer).call() == buys_tokens
    assert uncapped_token.functions.totalSupply().call() == buys_tokens
    assert ico.functions.tokensSold().call() == buys_tokens
    assert ico.functions.investorCount().call() == 1

    # Ether on every account
    assert ico.functions.weiRaised().call() == wei_value
    assert ico.functions.investedAmountOf(customer).call() == wei_value
    balance_diff = web3.eth.getBalance(team_multisig) - original_balance
    assert balance_diff == wei_value

    # Investors
    assert ico.functions.investorCount().call() == 1

    #
    # Events
    #

    # Crowdsale
    events = ico.events.Invested().createFilter(fromBlock=0).get_all_entries()
    assert len(events) == 1
    e = events[0]
    assert e["args"]["investor"] == customer
    assert e["args"]["weiAmount"] == wei_value
    assert e["args"]["tokenAmount"] == buys_tokens

    # ERC-20
    events = uncapped_token.events.Transfer().createFilter(fromBlock=0).get_all_entries()
    assert len(events) == 1
    e = events[0]
    assert e["args"]["from"] == "0x0000000000000000000000000000000000000000"
    assert e["args"]["to"] == customer
    assert e["args"]["value"] == buys_tokens


def test_buy_again(chain: TesterChain, web3: Web3, ico: Contract, uncapped_token: Contract, customer: str, preico_token_price, preico_starts_at, team_multisig):
    """Can buy more."""

    original_balance = web3.eth.getBalance(team_multisig)
    wei_value = to_wei(1, "ether")
    buys_tokens = wei_value // preico_token_price
    assert buys_tokens > 0

    time_travel(chain, preico_starts_at + 1)

    # Buy twice
    ico.functions.buy().transact({"from": customer, "value": wei_value})
    ico.functions.buy().transact({"from": customer, "value": wei_value})

    #
    # See everything was correctly credited
    #

    # Tokens on every account
    assert uncapped_token.functions.balanceOf(customer).call() == buys_tokens * 2
    assert uncapped_token.functions.totalSupply().call() == buys_tokens * 2
    assert ico.functions.tokensSold().call() == buys_tokens * 2

    # Ether on every account
    assert ico.functions.weiRaised().call() == wei_value * 2
    assert ico.functions.investedAmountOf(customer).call() == wei_value * 2
    balance_diff = web3.eth.getBalance(team_multisig) - original_balance
    assert balance_diff == wei_value * 2

    # Investors
    assert ico.functions.investorCount().call() == 1

    #
    # Events
    #

    # Crowdsale
    events = ico.events.Invested().createFilter(fromBlock=0).get_all_entries()
    assert len(events) == 2

    # ERC-20
    events = uncapped_token.events.Transfer().createFilter(fromBlock=0).get_all_entries()
    assert len(events) == 2


def test_buy_two_investors(chain: TesterChain, web3: Web3, ico: Contract, uncapped_token: Contract, customer: str, customer_2, preico_token_price, preico_starts_at, team_multisig):
    """Two different customers buy in."""

    original_balance = web3.eth.getBalance(team_multisig)
    wei_value = to_wei(1, "ether")
    buys_tokens = wei_value // preico_token_price
    assert buys_tokens > 0

    time_travel(chain, preico_starts_at + 1)

    # Buy twice
    ico.functions.buy().transact({"from": customer, "value": wei_value})
    ico.functions.buy().transact({"from": customer_2, "value": wei_value})

    #
    # See everything was correctly credited
    #

    # Tokens on every account
    assert uncapped_token.functions.balanceOf(customer).call() == buys_tokens
    assert uncapped_token.functions.totalSupply().call() == buys_tokens * 2
    assert ico.functions.tokensSold().call() == buys_tokens * 2

    # Ether on every account
    assert ico.functions.weiRaised().call() == wei_value * 2
    assert ico.functions.investedAmountOf(customer).call() == wei_value
    balance_diff = web3.eth.getBalance(team_multisig) - original_balance
    assert balance_diff == wei_value * 2

    # Investors
    assert ico.functions.investorCount().call() == 2

    #
    # Events
    #

    # Crowdsale
    events = ico.events.Invested().createFilter(fromBlock=0).get_all_entries()
    assert len(events) == 2

    # ERC-20
    events = uncapped_token.events.Transfer().createFilter(fromBlock=0).get_all_entries()
    assert len(events) == 2


def test_buy_reach_goal(chain: TesterChain, flat_pricing, ico: Contract, customer: str, preico_starts_at, preico_ends_at, preico_funding_goal):
    """Goal can be reached with a sufficient investment."""

    time_travel(chain, preico_starts_at + 1)
    wei_value = preico_funding_goal

    # Check that we don't have issues with our pricing
    assert flat_pricing.functions.calculatePrice(wei_value, 0, 0, customer, 0).call() > 0

    ico.functions.buy().transact({"from": customer, "value": wei_value})

    # We got investment event
    events = ico.events.Invested().createFilter(fromBlock=0).get_all_entries()
    assert len(events) == 1
    e = events[0]
    assert e["args"]["investor"] == customer
    assert e["args"]["weiAmount"] == wei_value

    assert ico.functions.weiRaised().call() == wei_value
    assert ico.functions.weiRaised().call() == ico.functions.minimumFundingGoal().call()
    assert ico.functions.isMinimumGoalReached().call()

    time_travel(chain, preico_ends_at + 1)
    assert ico.functions.getState().call() == CrowdsaleState.Success


def test_buy_fail_goal(chain: TesterChain, ico: Contract, customer: str, preico_starts_at, preico_ends_at, preico_funding_goal):
    """Goal is not reached if there is not enough investment."""

    time_travel(chain, preico_starts_at + 1)
    wei_value = preico_funding_goal // 2

    ico.functions.buy().transact({"from": customer, "value": wei_value})

    time_travel(chain, preico_ends_at + 1)
    assert ico.functions.getState().call() == CrowdsaleState.Failure


def test_buy_late_goal_not_reached(chain: TesterChain, ico: Contract, customer: str, preico_ends_at):
    """Cannot buy after closing time when the goal was not reached."""

    time_travel(chain, preico_ends_at + 1)
    assert ico.functions.getState().call() == CrowdsaleState.Failure
    with pytest.raises(TransactionFailed):
        ico.functions.buy().transact({"from": customer, "value": to_wei(1, "ether")})


def test_buy_late_goal_reached(chain: TesterChain, uncapped_flatprice_goal_reached: Contract, customer: str, preico_ends_at):
    """Cannot buy after closing time when the goal was not reached."""

    time_travel(chain, preico_ends_at + 1)
    assert uncapped_flatprice_goal_reached.functions.getState().call() == CrowdsaleState.Success
    with pytest.raises(TransactionFailed):
        uncapped_flatprice_goal_reached.functions.buy().transact({"from": customer, "value": to_wei(1, "ether")})


def test_buy_dust(chain: TesterChain, web3: Web3, ico: Contract, uncapped_token: Contract, customer: str, preico_token_price, preico_starts_at, team_multisig):
    """Cannot buy with too small transaction."""

    wei_value = 1

    time_travel(chain, preico_starts_at + 1)

    with pytest.raises(TransactionFailed):
        ico.functions.buy().transact({"from": customer, "value": wei_value})


def test_deposit_default_payabl(chain: TesterChain, web3: Web3, ico: Contract, uncapped_token: Contract, customer: str, preico_token_price, preico_starts_at, team_multisig):
    """Cannot just send money to the contract address and expect getting tokens.."""

    wei_value = to_wei(100, "ether")
    time_travel(chain, preico_starts_at + 1)
    with pytest.raises(TransactionFailed):
        web3.eth.sendTransaction({"from": customer, "value": wei_value, "to": ico.address})


def test_cannot_mint(chain: TesterChain, web3: Web3, ico: Contract, uncapped_token: Contract, customer: str, preico_token_price, preico_starts_at, team_multisig):
    """Only crowdsale contract can mint new tokens."""

    time_travel(chain, preico_starts_at + 1)

    with pytest.raises(TransactionFailed):
        uncapped_token.functions.mint(customer, 1000).transact({"from": customer})


def test_halt(chain: TesterChain, web3: Web3, ico: Contract, uncapped_token: Contract, customer: str, preico_token_price, preico_starts_at, team_multisig):
    """Cannot buy tokens during the emergency pause mode."""

    time_travel(chain, preico_starts_at + 1)
    wei_value = to_wei(1, "ether")

    ico.functions.halt().transact({"from": team_multisig})
    assert ico.functions.halted().call()

    with pytest.raises(TransactionFailed):
        ico.functions.buy().transact({"from": customer, "value": wei_value})

    ico.functions.unhalt().transact({"from": team_multisig})
    assert not ico.functions.halted().call()
    ico.functions.buy().transact({"from": customer, "value": wei_value})


def test_malicious_halt(chain: TesterChain, web3: Web3, ico: Contract, uncapped_token: Contract, malicious_address: str):
    """Only owner can pause."""

    with pytest.raises(TransactionFailed):
        ico.functions.halt().transact({"from": malicious_address})


def test_finalize(chain: TesterChain, web3: Web3, ico: Contract, malicious_address: str):
    """Crowdsale can be finalized and the tokens can be released."""

    with pytest.raises(TransactionFailed):
        ico.functions.halt().transact({"from": malicious_address})


def test_close_early(chain: TesterChain, ico: Contract, customer: str, preico_starts_at, preico_ends_at, team_multisig):
    """Soft cap triggered, close crowdsale early."""

    # Close earlier than anticipated
    new_early = preico_starts_at + 1*3600
    assert new_early < preico_ends_at

    time_travel(chain, preico_starts_at + 1)
    assert ico.functions.getState().call() == CrowdsaleState.Funding
    ico.functions.buy().transact({"from": customer, "value": to_wei(1, "ether")})
    ico.functions.setEndsAt(new_early).transact({"from": team_multisig})

    # Here we try to switch the strategy, and buy again, 1 wei for 1 token
    args = [
        1,
    ]
    tx = {
        "from": team_multisig,
    }
    pricing_strategy, hash = chain.provider.deploy_contract('FlatPricing', deploy_args=args, deploy_transaction=tx)

    ico.functions.setPricingStrategy(pricing_strategy.address).transact({"from": team_multisig})
    assert ico.functions.pricingStrategy().call() == pricing_strategy.address

    ico.functions.buy().transact({"from": customer, "value": 1})

    # Finally, here we travel in time to situation after the early closing:
    time_travel(chain, new_early + 1)
    assert ico.functions.getState().call() == CrowdsaleState.Failure

    with pytest.raises(TransactionFailed):
        ico.functions.buy().transact({"from": customer, "value": to_wei(1, "ether")})


def test_close_late(chain: TesterChain, ico: Contract, customer: str, preico_starts_at, preico_ends_at, team_multisig):
    """Extend crowdsale."""

    new_end = preico_ends_at + 1*3600
    assert new_end > preico_ends_at

    time_travel(chain, preico_starts_at + 1)
    assert ico.functions.getState().call() == CrowdsaleState.Funding
    ico.functions.buy().transact({"from": customer, "value": to_wei(1, "ether")})

    ico.functions.setEndsAt(new_end).transact({"from": team_multisig})

    time_travel(chain, preico_ends_at + 1)
    assert ico.functions.getState().call() == CrowdsaleState.Funding
    ico.functions.buy().transact({"from": customer, "value": to_wei(1, "ether")})


def test_change_end_at_only_owner(chain: TesterChain, ico: Contract, customer: str, preico_starts_at, preico_ends_at, team_multisig):
    """Only own can change end date."""

    new_early = preico_starts_at + 1*3600

    with pytest.raises(TransactionFailed):
        ico.functions.setEndsAt(new_early).transact({"from": customer})


def test_change_multisig(chain: TesterChain, ico: Contract, customer: str, preico_starts_at, preico_ends_at, team_multisig):
    """Owner can update the multisig address."""

    ico.functions.setMultisig(customer).transact({"from": team_multisig})
    assert ico.functions.multisigWallet().call() == customer


def test_change_multisig_only_owner(chain: TesterChain, ico: Contract, customer: str, preico_starts_at, preico_ends_at, team_multisig):
    """Only own can change the multisig address."""

    with pytest.raises(TransactionFailed):
        ico.functions.setMultisig(customer).transact({"from": customer})
