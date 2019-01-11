"""Preico proxy buy."""
import uuid

import pytest
from eth_utils import from_wei
from eth_utils import to_wei
from eth_tester.exceptions import TransactionFailed
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.state import CrowdsaleState


@pytest.fixture
def unlock_time(web3) -> int:
    # 4 week from now
    return web3.eth.getBlock('pending').timestamp + 4 * 7 * 24 * 60 * 60

@pytest.fixture()
def finalizer(chain, presale_crowdsale, uncapped_token, team_multisig) -> Contract:
    """Set crowdsale end strategy."""

    # Create finalizer contract
    args = [
        uncapped_token.address,
        presale_crowdsale.address,
    ]
    contract, hash = chain.provider.deploy_contract('DefaultFinalizeAgent', deploy_args=args)
    uncapped_token.functions.setReleaseAgent(contract.address).transact({"from": team_multisig})
    return contract


@pytest.fixture()
def crowdsale(chain, uncapped_flatprice, uncapped_token, team_multisig, finalizer) -> Contract:
    """Crowdsale used intests.."""
    uncapped_flatprice.transact({"from": team_multisig}).setFinalizeAgent(finalizer.address)

    assert uncapped_flatprice.functions.isFinalizerSane().call()
    assert uncapped_flatprice.functions.isPricingSane().call()

    time_travel(chain, uncapped_flatprice.functions.startsAt().call() + 1)
    assert uncapped_flatprice.functions.getState().call() == CrowdsaleState.Funding

    return uncapped_flatprice


@pytest.fixture()
def token(chain, uncapped_token, team_multisig) -> Contract:
    """Token used in tests"""
    return uncapped_token


@pytest.fixture()
def proxy_buyer_freeze_ends_at(chain, crowdsale) -> Contract:
    """When investors can reclaim."""
    return crowdsale.functions.endsAt().call() + 1


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
    crowdsale.functions.setPricingStrategy(tranche_pricing.address).transact({"from": team_multisig})
    return crowdsale


def test_proxy_buy(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Buy proxy as customer."""

    assert proxy_buyer.functions.getState().call() == 1
    assert proxy_buyer.functions.isPresale().call() == True

    #Change owner to customer_2, and back to team_multisig
    proxy_buyer.functions.transferOwnership(customer_2).transact({"from": team_multisig})
    proxy_buyer.functions.transferOwnership(team_multisig).transact({"from": customer_2})

    proxy_buyer.functions.buy().transact({"value": to_wei(10000, "ether"), "from": customer})
    proxy_buyer.functions.buy().transact({"value": to_wei(20000, "ether"), "from": customer_2})

    # Everything funder
    assert proxy_buyer.functions.weiRaised().call() == to_wei(30000, "ether")
    assert web3.eth.getBalance(proxy_buyer.address) == to_wei(30000, "ether")
    assert proxy_buyer.functions.balances(customer).call() == to_wei(10000, "ether")
    assert proxy_buyer.functions.balances(customer_2).call() == to_wei(20000, "ether")

    # Change the owner again, in the middle, and run rest of the test as customer_2
    proxy_buyer.functions.transferOwnership(customer_2).transact({"from": team_multisig})

    # Move over
    assert crowdsale.functions.getState().call() == CrowdsaleState.Funding
    proxy_buyer.functions.setCrowdsale(crowdsale.address).transact({"from": customer_2})
    assert proxy_buyer.functions.crowdsale().call() == web3.toChecksumAddress(crowdsale.address)
    proxy_buyer.functions.buyForEverybody().transact({"from": customer})
    assert web3.eth.getBalance(proxy_buyer.address) == 0

    # We got our tokens
    assert proxy_buyer.functions.getState().call() == 2
    assert proxy_buyer.functions.tokensBought().call() == 36000000
    assert proxy_buyer.functions.getClaimAmount(customer).call() == 36000000/3*1
    assert proxy_buyer.functions.getClaimLeft(customer).call() == 36000000/3*1
    assert proxy_buyer.functions.getClaimAmount(customer_2).call() == 36000000/3*2
    assert proxy_buyer.functions.getClaimLeft(customer_2).call() == 36000000/3*2

    # Tokens cannot be claimed before they are released
    time_travel(chain, crowdsale.functions.endsAt().call()+1)
    crowdsale.functions.finalize().transact({"from": team_multisig})
    assert token.functions.released().call()

    # Claim tokens
    proxy_buyer.functions.claimAll().transact({"from": customer})
    proxy_buyer.functions.claimAll().transact({"from": customer_2})

    # Check investors got their tokens
    assert proxy_buyer.functions.totalClaimed().call() == 36000000
    assert proxy_buyer.functions.claimCount().call() == 2
    assert proxy_buyer.functions.claimed(customer).call() == 36000000 / 3 * 1
    assert proxy_buyer.functions.claimed(customer_2).call() == 36000000 / 3 * 2
    assert token.functions.balanceOf(customer).call() == 36000000/3*1
    assert token.functions.balanceOf(customer_2).call() == 36000000/3*2


def test_proxy_buy_with_id(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Buy proxy as a customer we can link to a database entry."""

    assert proxy_buyer.functions.getState().call() == 1

    customer_id = int(uuid.uuid4().hex, 16)  # Customer ids are 128-bit UUID v4
    proxy_buyer.functions.buyWithCustomerId(customer_id).transact({"value": to_wei(10000, "ether"), "from": customer})

    events = proxy_buyer.events.Invested().createFilter(fromBlock=0).get_all_entries()
    assert len(events) == 1
    e = events[-1]
    assert e["args"]["customerId"] == customer_id


def test_proxy_buy_claim_twice(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Claim in two batches, uneven divide."""

    assert proxy_buyer.functions.getState().call() == 1

    proxy_buyer.transact({"value": to_wei(10000, "ether"), "from": customer}).buy()

    # Move over
    assert crowdsale.functions.getState().call() == CrowdsaleState.Funding
    proxy_buyer.functions.setCrowdsale(crowdsale.address).transact({"from": team_multisig})
    assert proxy_buyer.functions.crowdsale().call() == crowdsale.address
    proxy_buyer.functions.buyForEverybody().transact({"from": customer})

    # We got our tokens
    assert proxy_buyer.functions.getState().call() == 2
    assert proxy_buyer.functions.getClaimAmount(customer).call() == 12000000
    assert proxy_buyer.functions.getClaimLeft(customer).call() == 12000000
    assert proxy_buyer.functions.tokensBought().call() == 12000000

    # Tokens cannot be claimed before they are released
    time_travel(chain, crowdsale.functions.endsAt().call()+1)
    crowdsale.functions.finalize().transact({"from": team_multisig})
    assert token.functions.released().call()

    # Claim tokens
    proxy_buyer.functions.claim(int(12000000/2)).transact({"from": customer})
    assert proxy_buyer.functions.totalClaimed().call() == 12000000/2
    assert proxy_buyer.functions.claimCount().call() == 1
    assert proxy_buyer.functions.claimed(customer).call() == 12000000/2

    # Claim more
    assert proxy_buyer.functions.getClaimLeft(customer).call() == 12000000/2
    proxy_buyer.functions.claim(int(12000000/2)).transact({"from": customer})

    # Check investors got their tokens
    assert proxy_buyer.functions.totalClaimed().call() == 12000000
    assert proxy_buyer.functions.claimCount().call() == 1
    assert proxy_buyer.functions.claimed(customer).call() == 12000000
    assert token.functions.balanceOf(customer).call() == 12000000



def test_proxy_buy_refund(chain, web3, proxy_buyer, crowdsale, customer, customer_2):
    """We can refund"""

    value = to_wei(1, "ether")
    proxy_buyer.functions.buy().transact({"value": to_wei(10000, "ether"), "from": customer})
    proxy_buyer.functions.buy().transact({"value": to_wei(20000, "ether"), "from": customer_2})

    time_travel(chain, proxy_buyer.call().freezeEndsAt() + 1)
    assert proxy_buyer.functions.getState().call() == 3  # Refunding

    before_refund = web3.eth.getBalance(customer)
    proxy_buyer.transact({"from": customer}).refund()
    after_refund = web3.eth.getBalance(customer)

    assert from_wei(after_refund - before_refund, "ether") > 0.99  # gas cost epsilon
    assert proxy_buyer.functions.balances(customer).call() == 0


def test_proxy_buy_force_refund(chain, web3, proxy_buyer, crowdsale, customer, customer_2, team_multisig):
    """We force the contract into refund"""

    value = to_wei(1, "ether")
    proxy_buyer.functions.buy().transact({"value": to_wei(10000, "ether"), "from": customer})
    proxy_buyer.functions.buy().transact({"value": to_wei(20000, "ether"), "from": customer_2})

    proxy_buyer.functions.forceRefund().transact({"from": team_multisig})
    assert proxy_buyer.functions.getState().call() == 3  # Refunding

    before_refund = web3.eth.getBalance(customer)
    proxy_buyer.functions.refund().transact({"from": customer})
    after_refund = web3.eth.getBalance(customer)

    assert from_wei(after_refund - before_refund, "ether") > 0.99  # gas cost epsilon
    assert proxy_buyer.functions.balances(customer).call() == 0


def test_proxy_buy_load_refund(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Fail the crowdsale, refund the pre-investors"""

    assert proxy_buyer.functions.getState().call() == 1

    proxy_buyer.functions.buy().transact({"value": to_wei(10000, "ether"), "from": customer})

    # Move over
    assert crowdsale.functions.getState().call() == CrowdsaleState.Funding
    proxy_buyer.functions.setCrowdsale(crowdsale.address).transact({"from": team_multisig})
    assert proxy_buyer.functions.crowdsale().call() == crowdsale.address
    proxy_buyer.functions.buyForEverybody().transact({"from": customer})

    proxy_buyer.functions.forceRefund().transact({"from": team_multisig})
    proxy_buyer.functions.loadRefund().transact({"value": to_wei(10000, "ether"), "from": customer})

    before_refund = web3.eth.getBalance(customer)
    proxy_buyer.functions.refund().transact({"from": customer})
    after_refund = web3.eth.getBalance(customer)

    assert from_wei(after_refund - before_refund, "ether") > 0.99  # gas cost epsilon


def test_proxy_buy_move_funds_twice(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """We move funds only once."""

    assert proxy_buyer.functions.getState().call() == 1

    proxy_buyer.functions.buy().transact({"value": to_wei(10000, "ether"), "from": customer})
    proxy_buyer.functions.buy().transact({"value": to_wei(20000, "ether"), "from": customer_2})

    # Everything funder
    assert proxy_buyer.functions.weiRaised().call() == to_wei(30000, "ether")
    assert web3.eth.getBalance(proxy_buyer.address) == to_wei(30000, "ether")
    assert proxy_buyer.functions.balances(customer).call() == to_wei(10000, "ether")
    assert proxy_buyer.functions.balances(customer_2).call() == to_wei(20000, "ether")

    # Move over
    assert crowdsale.functions.getState().call() == CrowdsaleState.Funding
    proxy_buyer.functions.setCrowdsale(crowdsale.address).transact({"from": team_multisig})
    assert proxy_buyer.functions.crowdsale().call() == crowdsale.address
    proxy_buyer.functions.buyForEverybody().transact({"from": customer})

    with pytest.raises(TransactionFailed):
        proxy_buyer.functions.buyForEverybody().transact({"from": customer})


def test_proxy_buy_claim_too_much(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """You cannot claim more you got in the fair share"""

    assert proxy_buyer.functions.getState().call() == 1

    proxy_buyer.functions.buy().transact({"value": to_wei(10000, "ether"), "from": customer})
    proxy_buyer.functions.buy().transact({"value": to_wei(20000, "ether"), "from": customer_2})

    # Move over
    assert crowdsale.functions.getState().call() == CrowdsaleState.Funding
    proxy_buyer.functions.setCrowdsale(crowdsale.address).transact({"from": team_multisig})
    assert proxy_buyer.functions.crowdsale().call() == crowdsale.address
    proxy_buyer.functions.buyForEverybody().transact({"from": customer})

    # We got our tokens
    assert proxy_buyer.functions.getState().call() == 2
    assert proxy_buyer.functions.getClaimAmount(customer).call() == 12000000
    assert proxy_buyer.functions.getClaimLeft(customer).call() == 12000000
    assert proxy_buyer.functions.tokensBought().call() == 36000000

    # Tokens cannot be claimed before they are released
    time_travel(chain, crowdsale.functions.endsAt().call()+1)
    crowdsale.functions.finalize().transact({"from": team_multisig})
    assert token.functions.released().call()

    # Claim too many tokens
    with pytest.raises(TransactionFailed):
        proxy_buyer.functions.claim(12000000+1).transact({"from": customer})


def test_proxy_buy_too_much(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Try to buy over the cap."""

    assert proxy_buyer.functions.getState().call() == 1

    with pytest.raises(TransactionFailed):
        proxy_buyer.functions.buy().transact({"value": to_wei(100001, "ether"), "from": customer})

def test_proxy_min_buyin(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Try to buy over the cap."""

    assert proxy_buyer.functions.getState().call() == 1

    with pytest.raises(TransactionFailed):
        proxy_buyer.functions.buy().transact({"value": 1, "from": customer})

def test_proxy_max_buyin(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Try to buy over the cap."""

    assert proxy_buyer.functions.getState().call() == 1

    with pytest.raises(TransactionFailed):
        proxy_buyer.functions.buy().transact({"value": to_wei(44001, "ether"), "from": customer})


def test_proxy_buy_halted(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """Cannot buy when halted."""

    assert proxy_buyer.functions.getState().call() == 1

    proxy_buyer.functions.halt().transact({"from": team_multisig})

    with pytest.raises(TransactionFailed):
        proxy_buyer.functions.buy().transact({"value": to_wei(1, "ether"), "from": customer})


def test_proxy_buyforeverybody_halted(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """You cannot buy the tokens as non-owner if the contract is halted."""

    assert proxy_buyer.functions.getState().call() == 1

    proxy_buyer.functions.buy().transact({"value": to_wei(10000, "ether"), "from": customer})
    proxy_buyer.functions.buy().transact({"value": to_wei(20000, "ether"), "from": customer_2})

    # Move over
    assert crowdsale.functions.getState().call() == CrowdsaleState.Funding
    proxy_buyer.functions.setCrowdsale(crowdsale.address).transact({"from": team_multisig})
    assert proxy_buyer.functions.crowdsale().call() == crowdsale.address
    proxy_buyer.functions.halt().transact({"from": team_multisig})
    with pytest.raises(TransactionFailed):
        proxy_buyer.functions.buyForEverybody().transact({"from": customer})


def test_proxy_buyforeverybody_halted_owner(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token):
    """You cannot buy the tokens as non-owner if the contract is halted."""

    assert proxy_buyer.functions.getState().call() == 1

    proxy_buyer.functions.buy().transact({"value": to_wei(10000, "ether"), "from": customer})
    proxy_buyer.functions.buy().transact({"value": to_wei(20000, "ether"), "from": customer_2})

    # Move over
    assert crowdsale.functions.getState().call() == CrowdsaleState.Funding
    proxy_buyer.functions.setCrowdsale(crowdsale.address).transact({"from": team_multisig})
    assert proxy_buyer.functions.crowdsale().call() == crowdsale.address
    proxy_buyer.functions.halt().transact({"from": team_multisig})
    proxy_buyer.functions.buyForEverybody().transact({"from": team_multisig})


def test_proxy_buy_presale_pricing(chain, proxy_buyer, tranche_crowdsale, finalizer, token,  team_multisig, customer, customer_2, tranche_pricing):
    """Check that presale counters give a correct price.

    Presale investments should not count against tranches giving in the retail,
    but they are only effective in the main sale.
    """

    # We have set up the contracts in the way the presale purchaser gets special pricing
    assert tranche_crowdsale.functions.pricingStrategy().call() == chain.web3.toChecksumAddress(tranche_pricing.address)
    assert tranche_pricing.functions.isPresalePurchase(proxy_buyer.address).call() == True

    value = to_wei(20000, "ether")
    proxy_buyer.functions.buy().transact({"from": customer, "value": value})

    assert tranche_crowdsale.functions.getState().call() == CrowdsaleState.Funding

    # Load funds to ICO
    proxy_buyer.functions.setCrowdsale(tranche_crowdsale.address).transact({"from": team_multisig})
    proxy_buyer.functions.buyForEverybody().transact({"from": customer})

    # Check that raised counters were correctly upgraded
    assert tranche_crowdsale.functions.weiRaised().call() == to_wei(20000, "ether")
    assert tranche_crowdsale.functions.presaleWeiRaised().call() == to_wei(20000, "ether")

    # Tokens received, paid by preico price
    tranche_crowdsale.functions.investedAmountOf(proxy_buyer.address).call() == to_wei(20000, "ether")
    token.functions.balanceOf(proxy_buyer.address).call() == 20000 / 0.040

    # Do a normal investment, should go to tranche 1, as presale investment does not
    # count against tranches
    tranche_crowdsale.functions.buy().transact({"from": customer_2, "value": to_wei(10, "ether")})
    assert tranche_crowdsale.functions.presaleWeiRaised().call() == to_wei(20000, "ether")
    assert tranche_crowdsale.functions.weiRaised().call() == to_wei(20010, "ether")

    # We used tranche 1 price for customer despite already invested 20000 eth in presale
    # customer_2 got the tokens with tier 1 price
    token.functions.balanceOf(customer_2).call() == 10 / 0.00666666

    # Tokens cannot be claimed before they are released
    time_travel(chain, tranche_crowdsale.functions.endsAt().call()+1)
    tranche_crowdsale.functions.finalize().transact({"from": team_multisig})
    assert token.functions.released().call()

    # Check that presale participant gets his token with a presale price
    proxy_buyer.functions.claimAll().transact({"from": customer})
    token.functions.balanceOf(customer).call() == 20000 / 0.05

def test_proxy_timelock(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token, unlock_time):
    """Try to claim after timeLock has passed."""

    assert proxy_buyer.functions.getState().call() == 1
    assert proxy_buyer.functions.isPresale().call() == True

    #Change owner to customer_2, and back to team_multisig
    proxy_buyer.functions.setTimeLock(unlock_time).transact({"from": team_multisig})
    proxy_buyer.functions.transferOwnership(customer_2).transact({"from": team_multisig})
    proxy_buyer.functions.transferOwnership(team_multisig).transact({"from": customer_2})

    proxy_buyer.functions.buy().transact({"value": to_wei(10000, "ether"), "from": customer})
    proxy_buyer.functions.buy().transact({"value": to_wei(20000, "ether"), "from": customer_2})

    # Everything funder
    assert proxy_buyer.functions.weiRaised().call() == to_wei(30000, "ether")
    assert web3.eth.getBalance(proxy_buyer.address) == to_wei(30000, "ether")
    assert proxy_buyer.functions.balances(customer).call() == to_wei(10000, "ether")
    assert proxy_buyer.functions.balances(customer_2).call() == to_wei(20000, "ether")

    # Change the owner again, in the middle, and run rest of the test as customer_2
    proxy_buyer.functions.transferOwnership(customer_2).transact({"from": team_multisig})

    # Move over
    assert crowdsale.functions.getState().call() == CrowdsaleState.Funding
    proxy_buyer.functions.setCrowdsale(crowdsale.address).transact({"from": customer_2})
    assert proxy_buyer.functions.crowdsale().call() == crowdsale.address
    proxy_buyer.functions.buyForEverybody().transact({"from": customer})
    assert web3.eth.getBalance(proxy_buyer.address) == 0

    # We got our tokens
    assert proxy_buyer.functions.getState().call() == 2
    assert proxy_buyer.functions.tokensBought().call() == 36000000
    assert proxy_buyer.functions.getClaimAmount(customer).call() == 36000000/3*1
    assert proxy_buyer.functions.getClaimLeft(customer).call() == 36000000/3*1
    assert proxy_buyer.functions.getClaimAmount(customer_2).call() == 36000000/3*2
    assert proxy_buyer.functions.getClaimLeft(customer_2).call() == 36000000/3*2

    # Tokens cannot be claimed before they are released
    time_travel(chain, crowdsale.functions.endsAt().call()+1)
    crowdsale.functions.finalize().transact({"from": team_multisig})
    assert token.functions.released().call()
    time_travel(chain, unlock_time+1)

    # Claim tokens
    proxy_buyer.functions.claimAll().transact({"from": customer})
    proxy_buyer.functions.claimAll().transact({"from": customer_2})

    # Check investors got their tokens
    assert proxy_buyer.functions.totalClaimed().call() == 36000000
    assert proxy_buyer.functions.claimCount().call() == 2
    assert proxy_buyer.functions.claimed(customer).call() == 36000000 / 3 * 1
    assert proxy_buyer.functions.claimed(customer_2).call() == 36000000 / 3 * 2
    assert token.functions.balanceOf(customer).call() == 36000000/3*1
    assert token.functions.balanceOf(customer_2).call() == 36000000/3*2

def test_proxy_timelock_early(chain, web3, customer, customer_2, team_multisig, proxy_buyer, crowdsale, token, unlock_time):
    """Try to claim before timeLock has passed."""

    assert proxy_buyer.functions.getState().call() == 1
    assert proxy_buyer.functions.isPresale().call() == True

    #Change owner to customer_2, and back to team_multisig
    proxy_buyer.functions.setTimeLock(unlock_time).transact({"from": team_multisig})
    proxy_buyer.functions.transferOwnership(customer_2).transact({"from": team_multisig})
    proxy_buyer.functions.transferOwnership(team_multisig).transact({"from": customer_2})

    proxy_buyer.functions.buy().transact({"value": to_wei(10000, "ether"), "from": customer})
    proxy_buyer.functions.buy().transact({"value": to_wei(20000, "ether"), "from": customer_2})

    # Everything funder
    assert proxy_buyer.functions.weiRaised().call() == to_wei(30000, "ether")
    assert web3.eth.getBalance(proxy_buyer.address) == to_wei(30000, "ether")
    assert proxy_buyer.functions.balances(customer).call() == to_wei(10000, "ether")
    assert proxy_buyer.functions.balances(customer_2).call() == to_wei(20000, "ether")

    # Change the owner again, in the middle, and run rest of the test as customer_2
    proxy_buyer.functions.transferOwnership(customer_2).transact({"from": team_multisig})

    # Move over
    assert crowdsale.functions.getState().call() == CrowdsaleState.Funding
    proxy_buyer.functions.setCrowdsale(crowdsale.address).transact({"from": customer_2})
    assert proxy_buyer.functions.crowdsale().call() == crowdsale.address
    proxy_buyer.functions.buyForEverybody().transact({"from": customer})
    assert web3.eth.getBalance(proxy_buyer.address) == 0

    # We got our tokens
    assert proxy_buyer.functions.getState().call() == 2
    assert proxy_buyer.functions.tokensBought().call() == 36000000
    assert proxy_buyer.functions.getClaimAmount(customer).call() == 36000000/3*1
    assert proxy_buyer.functions.getClaimLeft(customer).call() == 36000000/3*1
    assert proxy_buyer.functions.getClaimAmount(customer_2).call() == 36000000/3*2
    assert proxy_buyer.functions.getClaimLeft(customer_2).call() == 36000000/3*2

    # Tokens cannot be claimed before they are released
    time_travel(chain, crowdsale.functions.endsAt().call()+1)
    crowdsale.functions.finalize().transact({"from": team_multisig})
    assert token.functions.released().call()

    # Claim tokens
    with pytest.raises(TransactionFailed):
        proxy_buyer.functions.claimAll().transact({"from": customer})
        proxy_buyer.functions.claimAll().transact({"from": customer_2})
