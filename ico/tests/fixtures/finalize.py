import pytest
from web3.contract import Contract


@pytest.fixture()
def default_finalize_agent(chain, uncapped_token, uncapped_flatprice) -> Contract:

    # Create finalizer contract
    args = [
        uncapped_token.address,
        uncapped_flatprice.address,
    ]
    contract, hash = chain.provider.deploy_contract('DefaultCrowdsaleFinal', deploy_args=args)
    return contract


@pytest.fixture
def uncapped_flatprice_final(chain, uncapped_token, uncapped_flatprice, team_multisig, default_finalize_agent) -> Contract:
    """A ICO contract where we have a default finalizer in place."""

    # Crowdsale calls this finalizer at the success
    uncapped_flatprice.transact({"from": team_multisig}).setFinalizeAgent(default_finalize_agent.address)

    # Token allows finalizer to release the tokens
    uncapped_token.transact({"from": team_multisig}).setReleaseAgent(default_finalize_agent.address)

    return uncapped_flatprice
