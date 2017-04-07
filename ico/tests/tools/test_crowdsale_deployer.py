"""YAML crowdsale definition loader."""

from ico.deploy import deploy_crowdsale
from ico.deploy import write_deployment_report
from ico.deploy import perform_post_actions
from ico.deploy import perform_verify_actions
from ico.definition import load_crowdsale_definitions


def test_deploy_crowdsale(chain, accounts, example_yaml_filename):
    """Deploy multiple contracts from a crowdsale definition file."""

    chain_data = load_crowdsale_definitions(example_yaml_filename, "unit_test")
    # Not needed for testnet
    chain_data["unlock_deploy_address"] = False
    # Dynamically set deploy address from testrpc address list
    chain_data["deploy_address"] = accounts[0]
    runtime_data, statistics, contracts = deploy_crowdsale(chain, chain_data)

    perform_post_actions(runtime_data, contracts)
    perform_verify_actions(runtime_data, contracts)
    write_deployment_report(example_yaml_filename, runtime_data)
