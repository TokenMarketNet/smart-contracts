"""YAML crowdsale definition loader."""

from ico.deploy import deploy_crowdsale
from ico.definition import load_crowdsale_definitions


def test_deploy_crowdsale(chain, accounts, example_yaml_filename):
    """Deploy multiple contracts from a crowdsale definition file."""

    chain_data = load_crowdsale_definitions(example_yaml_filename, "unit_test")
    # Not needed for testnet
    chain_data["unlock_deploy_address"] = False
    chain_data["deploy_address"] = accounts[0]
    return deploy_crowdsale(chain, chain_data)
