"""YAML crowdsale definition loader."""

from ico.deploy import deploy_crowdsale
from ico.deploy import write_deployment_report
from ico.deploy import perform_post_actions
from ico.deploy import perform_verify_actions
from ico.definition import load_crowdsale_definitions


def test_deploy_crowdsale(project, chain, accounts, example_yaml_filename):
    """Deploy multiple contracts from a crowdsale definition file."""

    chain_data = load_crowdsale_definitions(example_yaml_filename, "unit_test")
    # Not needed for testrpc
    chain_data["unlock_deploy_address"] = False

    runtime_data, statistics, contracts = deploy_crowdsale(project, chain, example_yaml_filename, chain_data, accounts[7])

    perform_post_actions(chain, runtime_data, contracts)
    perform_verify_actions(chain, runtime_data, contracts)
    write_deployment_report(example_yaml_filename, runtime_data)
