import datetime

import pytest
from eth_utils import to_wei
from web3.contract import Contract


@pytest.fixture
def release_agent(chain, team_multisig, token) -> Contract:
    """Create a simple release agent (useful for testing)."""

    args = [token.address]

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('SimpleReleaseAgent', deploy_args=args, deploy_transaction=tx)
    return contract


@pytest.fixture
def released_token(chain, team_multisig, token, release_agent, customer) -> Contract:
    """Create a Crowdsale token where transfer restrictions have been lifted."""

    token.functions.setReleaseAgent(release_agent.address).transact({"from": team_multisig})
    release_agent.functions.release().transact({"from": team_multisig})

    # Make sure customer 1 has some token balance
    token.functions.transfer(customer, 10000).transact({"from": team_multisig})

    return token


