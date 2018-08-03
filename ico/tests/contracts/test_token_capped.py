"""Token capped crowdsale."""
import pytest
from eth_utils import to_wei
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.state import CrowdsaleState


@pytest.fixture
def token(empty_token):
    """Get a token with 0 initial issuance."""
    return empty_token


@pytest.fixture
def start_time(web3) -> int:
    # 2 minutes from now
    return web3.eth.getBlock('pending').timestamp + 120


@pytest.fixture
def end_time(start_time) -> int:
    """Run 4 weeks."""
    return start_time + 4 * 7 * 24 * 3600


@pytest.fixture
def minimum_funding_goal() -> int:
    """What is our minimum funding goal."""
    return to_wei(7500, "ether")


@pytest.fixture
def cap() -> int:
    """What is our maximum tokens sold capacity."""
    return 4000000


@pytest.fixture
def founder_allocation() -> float:
    """How much tokens are allocated to founders, etc."""
    return 0.2


@pytest.fixture
def milestone_pricing(chain, start_time, end_time):
    """Milestone pricing, do not set presale collection contract."""

    week = 24*3600 * 7

    args = [
        [
            start_time + 0, to_wei("0.10", "ether"),
            start_time + week*1, to_wei("0.11", "ether"),
            start_time + week*2, to_wei("0.12", "ether"),
            start_time + week*3, to_wei("0.13", "ether"),
            end_time, 0,
        ]
    ]

    tx = {
        "gas": 3141592
    }
    contract, hash = chain.provider.deploy_contract('MilestonePricing', deploy_args=args, deploy_transaction=tx)
    return contract


@pytest.fixture
def crowdsale(chain, team_multisig, start_time, end_time, milestone_pricing, preico_cap, minimum_funding_goal, cap, token) -> Contract:
    """Create a crowdsale contract that has a minting cap and bonus % and token sold limit."""

    args = [
        token.address,
        milestone_pricing.address,
        team_multisig,
        start_time,
        end_time,
        minimum_funding_goal,
        cap
    ]

    tx = {
        "from": team_multisig,
    }

    contract, hash = chain.provider.deploy_contract('MintedTokenCappedCrowdsale', deploy_args=args, deploy_transaction=tx)

    assert contract.functions.owner().call() == team_multisig
    assert not token.functions.released().call()
    assert contract.functions.maximumSellableTokens().call() == cap

    # Allow crowdsale contract to do mint()
    token.functions.setMintAgent(contract.address, True).transact({"from": team_multisig})
    assert token.functions.mintAgents(contract.address).call() == True

    return contract


@pytest.fixture()
def finalizer(chain, token, crowdsale, team_multisig, founder_allocation) -> Contract:

    # Create finalizer contract
    args = [
        token.address,
        crowdsale.address,
        int(founder_allocation * 10000), # 20% for founders, bounties, etc.
        team_multisig, # Who gets extra tokens
    ]
    contract, hash = chain.provider.deploy_contract('BonusFinalizeAgent', deploy_args=args)

    # Set crowdsale finalizer

    # Allow finalzier to do mint()
    token.functions.setMintAgent(contract.address, True).transact({"from": team_multisig})
    assert token.functions.mintAgents(contract.address).call() == True

    token.functions.setReleaseAgent(contract.address).transact({"from": team_multisig})

    crowdsale.functions.setFinalizeAgent(contract.address).transact({"from": team_multisig})

    return contract


def test_buy_some(chain, crowdsale, token, finalizer, start_time, end_time, team_multisig, customer, minimum_funding_goal, founder_allocation):
    """Buy some token and finalize crowdsale."""

    # Buy on first week
    time_travel(chain, start_time + 1)
    assert crowdsale.functions.getState().call() == CrowdsaleState.Funding

    # Buy minimum funding goal
    wei_value = minimum_funding_goal
    crowdsale.functions.buy().transact({"from": customer, "value": wei_value})
    assert crowdsale.functions.isMinimumGoalReached().call()

    # Close the deal
    time_travel(chain, end_time + 1)
    assert crowdsale.functions.getState().call() == CrowdsaleState.Success
    crowdsale.functions.finalize().transact({"from": team_multisig})
    assert crowdsale.functions.getState().call() == CrowdsaleState.Finalized

    customer_tokens = 7500 / 0.10

    # See that we counted bonus correctly
    assert finalizer.functions.allocatedBonus().call() == customer_tokens * 0.2

    # See that bounty tokens do not count against tokens sold
    assert crowdsale.functions.tokensSold().call() == customer_tokens
    assert token.functions.totalSupply().call() == customer_tokens * (1+founder_allocation)

    # See that customers get their tokens
    assert token.functions.balanceOf(customer).call() == crowdsale.functions.tokensSold().call()

    # See that team multisig got our bonus tokens
    assert token.functions.balanceOf(team_multisig).call() == crowdsale.functions.tokensSold().call() * founder_allocation

    # Token is transferable
    assert token.functions.released().call()


def test_buy_all(chain, crowdsale, token, finalizer, start_time, end_time, team_multisig, customer, cap, founder_allocation):
    """Buy all tokens and finalize crowdsale."""

    # Buy on first week
    time_travel(chain, start_time + 1)
    assert crowdsale.functions.getState().call() == CrowdsaleState.Funding

    # Buy all cap
    wei_value = cap * to_wei("0.10", "ether")
    crowdsale.functions.buy().transact({"from": customer, "value": wei_value})
    assert crowdsale.functions.isCrowdsaleFull().call()

    # Close the deal
    time_travel(chain, end_time + 1)
    assert crowdsale.functions.getState().call() == CrowdsaleState.Success
    crowdsale.functions.finalize().transact({"from": team_multisig})
    assert crowdsale.functions.getState().call() == CrowdsaleState.Finalized

    customer_tokens = 4000000

    # See that we counted bonus correctly
    assert finalizer.functions.allocatedBonus().call() == 800000

    # See that bounty tokens do not count against tokens sold
    assert crowdsale.functions.tokensSold().call() == customer_tokens
    assert token.functions.totalSupply().call() == customer_tokens * (1 + founder_allocation)

    # See that customers get their tokens
    assert token.functions.balanceOf(customer).call() == crowdsale.functions.tokensSold().call()

    # See that team multisig got our bonus tokens
    assert token.functions.balanceOf(team_multisig).call() == crowdsale.functions.tokensSold().call() * founder_allocation

    # Token is transferable
    assert token.functions.released().call()
