import pytest
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

    aml_token.functions.setReleaseAgent(team_multisig).transact({"from": team_multisig})
    aml_token.functions.releaseTokenTransfer().transact({"from": team_multisig})

    # Make sure customer 1 has some token balance
    aml_token.functions.transfer(customer, 10000).transact({"from": team_multisig})

    return aml_token
