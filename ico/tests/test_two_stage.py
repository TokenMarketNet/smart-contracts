"""Two-state crowdsale."""
import pytest
from eth_utils import to_wei
from populus.chain import TestRPCChain
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.tests.utils import CrowdsaleState


@pytest.fixture
def preico(uncapped_flatprice: Contract):
    """First part of the crowdsale."""
    return uncapped_flatprice


@pytest.fixture
def token(uncapped_token: Contract):
    """The same uncapped token goes through both pre-ICO and ICO."""
    return uncapped_token


@pytest.fixture
def final_pricing(chain, preico_token_price) -> Contract:
    """In actual ICO, the price is doubled (for testing purposes)."""
    args = [
        preico_token_price * 2,
    ]
    pricing_strategy, hash = chain.provider.deploy_contract('FlatPricing', deploy_args=args)
    return pricing_strategy


@pytest.fixture
def actual_ico_starts_at(uncapped_flatprice: Contract, preico_ends_at):
    """The actual ICO is 90 after pre-ico."""
    return preico_ends_at + 24*3600 + 90


@pytest.fixture
def actual_ico_ends_at(uncapped_flatprice: Contract, actual_ico_starts_at):
    """ICO lasts 30 days."""
    return actual_ico_starts_at + 24*3600 + 30


@pytest.fixture
def actual_ico_funding_goal():
    """Actual ICO is only limited by time.s"""
    return to_wei(0, "ether")


@pytest.fixture
def actual_ico(chain, uncapped_token: Contract, team_multisig, beneficiary, final_pricing, actual_ico_starts_at, actual_ico_ends_at, actual_ico_funding_goal):
    """Second part of the crowdsale."""

    token = uncapped_token

    args = [
        token.address,
        final_pricing.address,
        team_multisig,
        beneficiary,
        actual_ico_starts_at,
        actual_ico_ends_at,
        actual_ico_funding_goal,
    ]

    tx = {
        "from": team_multisig,
    }

    contract, hash = chain.provider.deploy_contract('UncappedFlatpriceICO', deploy_args=args, deploy_transaction=tx)

    assert contract.call().owner() == team_multisig
    assert not token.call().released()

    # Allow actual ico contract to do mint()
    token.transact({"from": team_multisig}).setMintAgent(contract.address, True)
    assert token.call().mintAgents(contract.address) == True

    # The success of the actual ICO can make the token transferable
    # Create finalizer contract
    args = [
        uncapped_token.address,
        contract.address,
    ]
    finalizing_agent, hash = chain.provider.deploy_contract('DefaultCrowdsaleFinal', deploy_args=args)
    contract.transact({"from": team_multisig}).setFinalizeAgent(finalizing_agent.address)  # Crowdsale calls this finalizer at the success
    uncapped_token.transact({"from": team_multisig}).setReleaseAgent(finalizing_agent.address)

    return contract


def test_two_stage_initialized(preico, actual_ico, token, team_multisig, preico_starts_at, preico_ends_at, actual_ico_starts_at, actual_ico_ends_at, preico_funding_goal, actual_ico_funding_goal):
    """Two-stage ICO is properly initialized."""

    # We have owner
    assert preico.call().owner() == team_multisig
    assert actual_ico.call().owner() == team_multisig

    # Crowdsale contract is in minters
    assert token.call().mintAgents(actual_ico.address) == True
    assert token.call().mintAgents(preico.address) == True
    assert not token.call().released()
    assert not preico.call().halted()
    assert not actual_ico.call().halted()
    assert preico.call().startsAt() == preico_starts_at
    assert preico.call().endsAt() == preico_ends_at
    assert actual_ico.call().startsAt() == actual_ico_starts_at
    assert actual_ico.call().endsAt() == actual_ico_ends_at

    assert preico.call().getState() == CrowdsaleState.PreFunding
    assert preico.call().minimumFundingGoal() == preico_funding_goal

    assert actual_ico.call().getState() == CrowdsaleState.PreFunding
    assert actual_ico.call().minimumFundingGoal() == actual_ico_funding_goal

    assert preico_ends_at < actual_ico_starts_at


def test_buy_both_stages(chain: TestRPCChain, preico: Contract, actual_ico: Contract, uncapped_token: Contract, customer, customer_2, preico_starts_at, preico_ends_at, actual_ico_starts_at, actual_ico_ends_at, flat_pricing, final_pricing):
    """We run ICOs in several stages and investors can participate every round.

    In this test we do pre-ICO and ICO. Pre-ICO has a minimum funding goal. The tokens are not released for transfer until the actual ICO is over. Both rounds are uncapped and new tokens get minted for investors.
    """

    # The token contract used in this test
    token = uncapped_token

    # First buy tokens when pre-ICO is open
    first_buy = to_wei(100000, "ether")
    first_batch = flat_pricing.call().calculatePrice(first_buy, 0, 0)
    time_travel(chain, preico_starts_at + 1)
    assert preico.call().getState() == CrowdsaleState.Funding
    assert actual_ico.call().getState() == CrowdsaleState.PreFunding
    preico.transact({"from": customer, "value": first_buy}).buy()

    # Finalize the pre-ICO does nothing, but can be still called
    time_travel(chain, preico_ends_at + 1)
    assert preico.call().getState() == CrowdsaleState.Success
    preico.transact({"from": customer}).finalize()
    assert not token.call().released() # Still on hold

    # Then buy more tokens when the actual ICO is open
    time_travel(chain, actual_ico_starts_at + 1)
    assert actual_ico.call().getState() == CrowdsaleState.Funding
    second_buy = to_wei(2, "ether")
    second_batch = final_pricing.call().calculatePrice(second_buy, 0, 0)
    actual_ico.transact({"from": customer, "value": second_buy}).buy()

    # Close the actual ICO and check tokens are transferable
    time_travel(chain, actual_ico_ends_at + 1)
    assert actual_ico.call().getState() == CrowdsaleState.Success
    actual_ico.transact({"from": customer}).finalize()
    assert actual_ico.call().finalized()
    assert token.call().released()

    # We got our tokens from both ICO buys
    token.call().balanceOf(customer) == first_batch + second_batch

    # Transfer tokens between accounts
    token.transact({"from": customer}).transfer(customer_2, 2000)
    assert token.call().balanceOf(customer_2) == 2000
