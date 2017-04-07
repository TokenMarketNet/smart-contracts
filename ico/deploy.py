"""Deploy contracts from crowdsale defifinitions."""
import copy
from collections import Counter
from typing import Tuple

import jinja2
import ruamel.yaml
from populus.utils.cli import request_account_unlock
from populus.utils.accounts import is_account_locked

from ico.definition import load_crowdsale_definitions
from ico.definition import get_jinja_context
from ico.definition import interpolate_data
from ico.utils import get_constructor_arguments


def get_etherscan_link(network, address):
    """Construct etherscan link"""

    if network == "mainnet":
        return "https://etherscan.io/address/" + address
    elif network == "ropsten":
        return "https://etherscan.io/address/" + address
    else:
        raise RuntimeError("Unknown network: {}".format(network))


def deploy_contract(chain, deploy_address, contract_def: dict, chain_name: str, verify=False, need_unlock=True):
    """Deploy a single contract."""

    contract_name = contract_def["contract_name"]

    web3 = chain.web3

    # Goes through geth account unlock process if needed
    if need_unlock:
        if is_account_locked(web3, deploy_address):
            request_account_unlock(chain, deploy_address, None)

    transaction = {"from": deploy_address}
    kwargs = dict(**contract_def["arguments"])  # Unwrap YAML CommentedMap

    print("Starting", contract_name, "deployment, with arguments ", kwargs)
    try:
        contract, txhash = chain.provider.deploy_contract(contract_name, deploy_transaction=transaction, deploy_kwargs=kwargs)
    except Exception as e:
        raise RuntimeError("Could not deploy contract {}, constructor arguments {}".format(contract_name, kwargs)) from e

    contract_def["address"] = contract.address
    print(contract_name, "address is", contract.address)

    constructor_args = get_constructor_arguments(contract, kwargs=kwargs)
    print(contract_name, "constructor arguments payload is", constructor_args)
    contract_def["constructor_args"] = constructor_args

    contract_def["link"] = get_etherscan_link(chain_name, contract.address)



def deploy_crowdsale(chain, source_definitions: dict) -> Tuple[dict, dict]:
    """Deploy multiple contracts from crowdsale definitions.

    :param chain: Populus chain object
    :param data: One of mainnet/ropsten parsed data definitions in a YAML file
    :return: Tuple (expaneded definitions, statistics). The expanded definitions are run-time data that has everything expanded out and actual contract addresses
    """

    statistics = Counter()

    # This will contain our output and parsed values
    runtime_data = copy.deepcopy(source_definitions)

    deploy_address = runtime_data["deploy_address"]
    chain_name = runtime_data["chain"]

    need_unlock = runtime_data.get("unlock_deploy_address", True)

    for name, contract_def in runtime_data["contracts"].items():

        # First expand out all variables
        address = contract_def.get("address")
        if address:
            print("Already deployed contract,", name, address)
            statistics["already_deployed"] += 1
            continue

        # Expand Jinja templated variables for this contract
        context = get_jinja_context(runtime_data)

        try:
            expanded_contract_def = interpolate_data(contract_def, context)
        except jinja2.exceptions.TemplateError as e:
            raise RuntimeError("Could not expand data for section {}".format(name)) from e

        # Store expanded data for output
        runtime_data["contracts"][name] = expanded_contract_def

        deploy_contract(chain, deploy_address, expanded_contract_def, chain_name, need_unlock=need_unlock)
        statistics["deployed"] += 1

    return runtime_data, statistics


def write_deployment_report(yaml_filename: str, runtime_data: dict):
    """Write run-time data to a result file, so that it can easily inspected and shared."""

    report_filename = yaml_filename.replace(".yml", ".deployment-report.yml")
    with open(report_filename, "wt") as out:
        out.write(ruamel.yaml.round_trip_dump(runtime_data))


def deploy_crowdsale_from_file(chain, deployment_name, yaml_filename):
    chain_data = load_crowdsale_definitions(yaml_filename, deployment_name)
    return deploy_crowdsale(chain, chain_data)

