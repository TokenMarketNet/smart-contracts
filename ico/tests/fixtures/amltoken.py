import datetime

import pytest
from eth_utils import to_wei
from web3.contract import Contract

@pytest.fixture
def aml_token(chain, team_multisig, token_name, token_symbol, initial_supply) -> Contract:
    """Create the token contract."""

    args = [token_name, token_symbol, initial_supply, 0, True]  # Owner set

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('AMLToken', deploy_args=args, deploy_transaction=tx)
    return contract

@pytest.fixture
def released_aml_token(chain, team_multisig, aml_token, release_agent, customer) -> Contract:
    """Create a Crowdsale token where transfer restrictions have been lifted."""

    aml_token.transact({"from": team_multisig}).setReleaseAgent(team_multisig)
    aml_token.transact({"from": team_multisig}).releaseTokenTransfer()

    # Make sure customer 1 has some token balance
    aml_token.transact({"from": team_multisig}).transfer(customer, 10000)

    return aml_token
