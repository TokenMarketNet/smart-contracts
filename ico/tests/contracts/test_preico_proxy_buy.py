"""Preico proxy buy."""
import uuid

import pytest
from eth_utils import from_wei
from eth_utils import to_wei
from ethereum.tester import TransactionFailed
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.state import CrowdsaleState


@pytest.fixture()
def finalizer(chain, presale_crowdsale, uncapped_token, team_multisig) -> Contract:
    """Set crowdsale end strategy."""

    # Create finalizer contract
    args = [
        uncapped_token.address,
        presale_crowdsale.address,
    ]
    contract, hash = chain.provider.deploy_contract('DefaultFinalizeAgent', deploy_args=args)
    uncapped_token.transact({"from": team_multisig}).setReleaseAgent(contract.address)
    return contract


@pytest.fixture()
def crowdsale(chain, uncapped_flatprice, uncapped_token, team_multisig, finalizer) -> Contract:
    """Crowdsale used intests.."""
    uncapped_flatprice.transact({"from": team_multisig}).setFinalizeAgent(finalizer.address)

    assert uncapped_flatprice.call().isFinalizerSane()
    assert uncapped_flatprice.call().isPricingSane()

    time_travel(chain, uncapped_flatprice.call().startsAt() + 1)
    assert uncapped_flatprice.call().getState() == CrowdsaleState.Funding

    return uncapped_flatprice


@pytest.fixture()
def token(chain, uncapped_token, team_multisig) -> Contract:
    """Token used in tests"""
    return uncapped_token


@pytest.fixture()
def proxy_buyer_freeze_ends_at(chain, crowdsale) -> Contract:
    """When investors can reclaim."""
    return crowdsale.call().endsAt() + 1


@pytest.fixture()
def proxy_buyer(chain, uncapped_token, proxy_buyer_freeze_ends_at, team_multisig) -> Contract:
    """Token used in tests"""

    # Create finalizer contract
    args = [
        team_multisig,
        proxy_buyer_freeze_ends_at,
        2,  # 2 wei, to be able to test minimum buyin
        to_wei(41000, "ether"),
        to_wei(100000, "ether"),
    ]
    contract, hash = chain.provider.deploy_contract('PreICOProxyBuyer', deploy_args=args)
    return contract



@pytest.fixture
def tranche_pricing(chain, proxy_buyer, team_multisig):
    """ETH tanche pricing for testing presale counters."""
    args = [
        [
            to_wei("0", "ether"), to_wei("0.00666666", "ether"),
            to_wei("10001", "ether"), to_wei("0.00714285", "ether"),
            to_wei("30001", "ether"), to_wei("0.00769230", "ether"),
            to_wei("50001", "ether"), to_wei("0.00833333", "ether"),
            to_wei("75001", "ether"), to_wei("0.00909090", "ether"),
            to_wei("100001", "ether"), to_wei("0.01000000", "ether"),
            to_wei("1000000000", "ether"), to_wei("0.01000000", "ether"),
            to_wei("1000000000000", "ether"), to_wei("0.00", "ether")
        ],
    ]

    tx = {
        "from": team_multisig
    }
    contract, hash = chain.provider.deploy_contract('EthTranchePricing', deploy_args=args, deploy_transaction=tx)

    contract.transact({"from": team_multisig}).setPreicoAddress(proxy_buyer.address, to_wei("0.05", "ether"))
    return contract


@pytest.fixture()
def tranche_crowdsale(chain, crowdsale, tranche_pricing, uncapped_token, team_multisig, finalizer) -> Contract:
    """A crowdsale with tranches and a special price for presale participants."""
    crowdsale.transact({"from": team_multisig}).setPricingStrategy(tranche_pricing.address)
    return crowdsale


def test_proxy_buy(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Buy proxy as customer."""

    assert proxy_buyer.call().getState() == 1
    assert proxy_buyer.call().isPresale() == True

    #Change owner to customer_2, and back to team_multisig
    proxy_buyer.transact({"from": team_multisig}).transferOwnership(customer_2)
    proxy_buyer.transact({"from": customer_2}).transferOwnership(team_multisig)

    proxy_buyer.transact({"value": to_wei(10000, "ether"), "from": customer}).buy()
    proxy_buyer.transact({"value": to_wei(20000, "ether"), "from": customer_2}).buy()

    # Everything funder
    assert proxy_buyer.call().weiRaised() == to_wei(30000, "ether")
    assert web3.eth.getBalance(proxy_buyer.address) == to_wei(30000, "ether")
    assert proxy_buyer.call().balances(customer) == to_wei(10000, "ether")
    assert proxy_buyer.call().balances(customer_2) == to_wei(20000, "ether")

    # Change the owner again, in the middle, and run rest of the test as customer_2
    proxy_buyer.transact({"from": team_multisig}).transferOwnership(customer_2)

    # Move over
    assert crowdsale.call().getState() == CrowdsaleState.Funding
    proxy_buyer.transact({"from": customer_2}).setCrowdsale(crowdsale.address)
    assert proxy_buyer.call().crowdsale() == crowdsale.address
    proxy_buyer.transact({"from": customer}).buyForEverybody()
    assert web3.eth.getBalance(proxy_buyer.address) == 0

    # We got our tokens
    assert proxy_buyer.call().getState() == 2
    assert proxy_buyer.call().tokensBought() == 36000000
    assert proxy_buyer.call().getClaimAmount(customer) == 36000000/3*1
    assert proxy_buyer.call().getClaimLeft(customer) == 36000000/3*1
    assert proxy_buyer.call().getClaimAmount(customer_2) == 36000000/3*2
    assert proxy_buyer.call().getClaimLeft(customer_2) == 36000000/3*2

    # Tokens cannot be claimed before they are released
    time_travel(chain, crowdsale.call().endsAt()+1)
    crowdsale.transact({"from": team_multisig}).finalize()
    assert token.call().released()

    # Claim tokens
    proxy_buyer.transact({"from": customer}).claimAll()
    proxy_buyer.transact({"from": customer_2}).claimAll()

    # Check investors got their tokens
    assert proxy_buyer.call().totalClaimed() == 36000000
    assert proxy_buyer.call().claimCount() == 2
    assert proxy_buyer.call().claimed(customer) == 36000000 / 3 * 1
    assert proxy_buyer.call().claimed(customer_2) == 36000000 / 3 * 2
    assert token.call().balanceOf(customer) == 36000000/3*1
    assert token.call().balanceOf(customer_2) == 36000000/3*2


def test_proxy_buy_with_id(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Buy proxy as a customer we can link to a database entry."""

    assert proxy_buyer.call().getState() == 1

    customer_id = int(uuid.uuid4().hex, 16)  # Customer ids are 128-bit UUID v4
    proxy_buyer.transact({"value": to_wei(10000, "ether"), "from": customer}).buyWithCustomerId(customer_id)

    events = proxy_buyer.pastEvents("Invested").get()
    assert len(events) == 1
    e = events[-1]
    assert e["args"]["customerId"] == customer_id


def test_proxy_buy_claim_twice(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Claim in two batches, uneven divide."""

    assert proxy_buyer.call().getState() == 1

    proxy_buyer.transact({"value": to_wei(10000, "ether"), "from": customer}).buy()

    # Move over
    assert crowdsale.call().getState() == CrowdsaleState.Funding
    proxy_buyer.transact({"from": team_multisig}).setCrowdsale(crowdsale.address)
    assert proxy_buyer.call().crowdsale() == crowdsale.address
    proxy_buyer.transact({"from": customer}).buyForEverybody()

    # We got our tokens
    assert proxy_buyer.call().getState() == 2
    assert proxy_buyer.call().getClaimAmount(customer) == 12000000
    assert proxy_buyer.call().getClaimLeft(customer) == 12000000
    assert proxy_buyer.call().tokensBought() == 12000000

    # Tokens cannot be claimed before they are released
    time_travel(chain, crowdsale.call().endsAt()+1)
    crowdsale.transact({"from": team_multisig}).finalize()
    assert token.call().released()

    # Claim tokens
    proxy_buyer.transact({"from": customer}).claim(int(12000000/2))
    assert proxy_buyer.call().totalClaimed() == 12000000/2
    assert proxy_buyer.call().claimCount() == 1
    assert proxy_buyer.call().claimed(customer) == 12000000/2

    # Claim more
    assert proxy_buyer.call().getClaimLeft(customer) == 12000000/2
    proxy_buyer.transact({"from": customer}).claim(int(12000000/2))

    # Check investors got their tokens
    assert proxy_buyer.call().totalClaimed() == 12000000
    assert proxy_buyer.call().claimCount() == 1
    assert proxy_buyer.call().claimed(customer) == 12000000
    assert token.call().balanceOf(customer) == 12000000



def test_proxy_buy_refund(chain, web3, proxy_buyer, crowdsale, customer, customer_2):
    """We can refund"""

    value = to_wei(1, "ether")
    proxy_buyer.transact({"value": to_wei(10000, "ether"), "from": customer}).buy()
    proxy_buyer.transact({"value": to_wei(20000, "ether"), "from": customer_2}).buy()

    time_travel(chain, proxy_buyer.call().freezeEndsAt() + 1)
    assert proxy_buyer.call().getState() == 3  # Refunding

    before_refund = web3.eth.getBalance(customer)
    proxy_buyer.transact({"from": customer}).refund()
    after_refund = web3.eth.getBalance(customer)

    assert from_wei(after_refund - before_refund, "ether") > 0.99  # gas cost epsilon
    assert proxy_buyer.call().balances(customer) == 0


def test_proxy_buy_move_funds_twice(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """We move funds only once."""

    assert proxy_buyer.call().getState() == 1

    proxy_buyer.transact({"value": to_wei(10000, "ether"), "from": customer}).buy()
    proxy_buyer.transact({"value": to_wei(20000, "ether"), "from": customer_2}).buy()

    # Everything funder
    assert proxy_buyer.call().weiRaised() == to_wei(30000, "ether")
    assert web3.eth.getBalance(proxy_buyer.address) == to_wei(30000, "ether")
    assert proxy_buyer.call().balances(customer) == to_wei(10000, "ether")
    assert proxy_buyer.call().balances(customer_2) == to_wei(20000, "ether")

    # Move over
    assert crowdsale.call().getState() == CrowdsaleState.Funding
    proxy_buyer.transact({"from": team_multisig}).setCrowdsale(crowdsale.address)
    assert proxy_buyer.call().crowdsale() == crowdsale.address
    proxy_buyer.transact({"from": customer}).buyForEverybody()

    with pytest.raises(TransactionFailed):
        proxy_buyer.transact({"from": customer}).buyForEverybody()


def test_proxy_buy_claim_too_much(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """You cannot claim more you got in the fair share"""

    assert proxy_buyer.call().getState() == 1

    proxy_buyer.transact({"value": to_wei(10000, "ether"), "from": customer}).buy()
    proxy_buyer.transact({"value": to_wei(20000, "ether"), "from": customer_2}).buy()

    # Move over
    assert crowdsale.call().getState() == CrowdsaleState.Funding
    proxy_buyer.transact({"from": team_multisig}).setCrowdsale(crowdsale.address)
    assert proxy_buyer.call().crowdsale() == crowdsale.address
    proxy_buyer.transact({"from": customer}).buyForEverybody()

    # We got our tokens
    assert proxy_buyer.call().getState() == 2
    assert proxy_buyer.call().getClaimAmount(customer) == 12000000
    assert proxy_buyer.call().getClaimLeft(customer) == 12000000
    assert proxy_buyer.call().tokensBought() == 36000000

    # Tokens cannot be claimed before they are released
    time_travel(chain, crowdsale.call().endsAt()+1)
    crowdsale.transact({"from": team_multisig}).finalize()
    assert token.call().released()

    # Claim too many tokens
    with pytest.raises(TransactionFailed):
        proxy_buyer.transact({"from": customer}).claim(12000000+1)


def test_proxy_buy_too_much(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Try to buy over the cap."""

    assert proxy_buyer.call().getState() == 1

    with pytest.raises(TransactionFailed):
        proxy_buyer.transact({"value": to_wei(100001, "ether"), "from": customer}).buy()

def test_proxy_min_buyin(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Try to buy over the cap."""

    assert proxy_buyer.call().getState() == 1

    with pytest.raises(TransactionFailed):
        proxy_buyer.transact({"value": 1, "from": customer}).buy()

def test_proxy_max_buyin(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Try to buy over the cap."""

    assert proxy_buyer.call().getState() == 1

    with pytest.raises(TransactionFailed):
        proxy_buyer.transact({"value": to_wei(44001, "ether"), "from": customer}).buy()


def test_proxy_buy_halted(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Cannot buy when halted."""

    assert proxy_buyer.call().getState() == 1

    proxy_buyer.transact({"from": team_multisig}).halt()

    with pytest.raises(TransactionFailed):
        proxy_buyer.transact({"value": to_wei(1, "ether"), "from": customer}).buy()


def test_proxy_buyforeverybody_halted(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """You cannot buy the tokens as non-owner if the contract is halted."""

    assert proxy_buyer.call().getState() == 1

    proxy_buyer.transact({"value": to_wei(10000, "ether"), "from": customer}).buy()
    proxy_buyer.transact({"value": to_wei(20000, "ether"), "from": customer_2}).buy()

    # Move over
    assert crowdsale.call().getState() == CrowdsaleState.Funding
    proxy_buyer.transact({"from": team_multisig}).setCrowdsale(crowdsale.address)
    assert proxy_buyer.call().crowdsale() == crowdsale.address
    proxy_buyer.transact({"from": team_multisig}).halt()
    with pytest.raises(TransactionFailed):
        proxy_buyer.transact({"from": customer}).buyForEverybody()


def test_proxy_buyforeverybody_halted_owner(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """You cannot buy the tokens as non-owner if the contract is halted."""

    assert proxy_buyer.call().getState() == 1

    proxy_buyer.transact({"value": to_wei(10000, "ether"), "from": customer}).buy()
    proxy_buyer.transact({"value": to_wei(20000, "ether"), "from": customer_2}).buy()

    # Move over
    assert crowdsale.call().getState() == CrowdsaleState.Funding
    proxy_buyer.transact({"from": team_multisig}).setCrowdsale(crowdsale.address)
    assert proxy_buyer.call().crowdsale() == crowdsale.address
    proxy_buyer.transact({"from": team_multisig}).halt()
    proxy_buyer.transact({"from": team_multisig}).buyForEverybody()


def test_proxy_buy_presale_pricing(chain, proxy_buyer, tranche_crowdsale, finalizer, token,  team_multisig, customer, customer_2, tranche_pricing):
    """Check that presale counters give a correct price.

    Presale investments should not count against tranches giving in the retail,
    but they are only effective in the main sale.
    """

    # We have set up the contracts in the way the presale purchaser gets special pricing
    assert tranche_crowdsale.call().pricingStrategy() == tranche_pricing.address
    assert tranche_pricing.call().isPresalePurchase(proxy_buyer.address) == True

    value = to_wei(20000, "ether")
    proxy_buyer.transact({"from": customer, "value": value}).buy()

    assert tranche_crowdsale.call().getState() == CrowdsaleState.Funding

    # Load funds to ICO
    proxy_buyer.transact({"from": team_multisig}).setCrowdsale(tranche_crowdsale.address)
    proxy_buyer.transact({"from": customer}).buyForEverybody()

    # Check that raised counters were correctly upgraded
    assert tranche_crowdsale.call().weiRaised() == to_wei(20000, "ether")
    assert tranche_crowdsale.call().presaleWeiRaised() == to_wei(20000, "ether")

    # Tokens received, paid by preico price
    tranche_crowdsale.call().investedAmountOf(proxy_buyer.address) == to_wei(20000, "ether")
    token.call().balanceOf(proxy_buyer.address) == 20000 / 0.040

    # Do a normal investment, should go to tranche 1, as presale investment does not
    # count against tranches
    tranche_crowdsale.transact({"from": customer_2, "value": to_wei(10, "ether")}).buy()
    assert tranche_crowdsale.call().presaleWeiRaised() == to_wei(20000, "ether")
    assert tranche_crowdsale.call().weiRaised() == to_wei(20010, "ether")

    # We used tranche 1 price for customer despite already invested 20000 eth in presale
    # customer_2 got the tokens with tier 1 price
    token.call().balanceOf(customer_2) == 10 / 0.00666666

    # Tokens cannot be claimed before they are released
    time_travel(chain, tranche_crowdsale.call().endsAt()+1)
    tranche_crowdsale.transact({"from": team_multisig}).finalize()
    assert token.call().released()

    # Check that presale participant gets his token with a presale price
    proxy_buyer.transact({"from": customer}).claimAll()
    token.call().balanceOf(customer) == 20000 / 0.05


def test_proxy_buy_destroy(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Our escape mechanism if something goes wrong."""

    assert proxy_buyer.call().getState() == 1

    proxy_buyer.transact({"value": to_wei(10000, "ether"), "from": customer}).buy()
    customer_balance = web3.eth.getBalance(customer) # Simpler to do this after gas usage

    proxy_buyer.transact({"from": team_multisig}).destroyAndSend(customer)
    assert web3.eth.getBalance(customer) == (customer_balance + to_wei(10000, "ether"))
