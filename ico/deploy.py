"""Deploy contracts from crowdsale defifinitions."""
import copy
import textwrap
from collections import Counter
from collections import defaultdict
from typing import Tuple
import os
import time

import jinja2
import ruamel.yaml

from eth_utils import from_wei

from populus import Project
from populus.utils.cli import request_account_unlock
from populus.utils.accounts import is_account_locked
from web3.contract import Contract

from ico.utils import get_contract_by_name
from ico.definition import load_crowdsale_definitions
from ico.definition import get_jinja_context
from ico.definition import interpolate_data
from ico.definition import get_post_actions_context
from ico.utils import get_constructor_arguments
from ico.utils import asbool
from ico.utils import get_libraries
from ico.etherscan import verify_contract
from ico.etherscan import get_etherscan_link


def deploy_contract(project: Project, chain, deploy_address, contract_def: dict, chain_name: str, need_unlock=True) -> Contract:
    """Deploy a single contract.

    :param need_unlock: Do the account unlock procedure (disable for testrpc)
    """

    web3 = chain.web3

    contract_name = contract_def["contract_name"]

    version = web3.version.node

    # Goes through geth account unlock process if needed
    if need_unlock and version.startswith("Geth"):
        # TODO:  Parity does not support this, must unlock on a command line, or web ui?
        if is_account_locked(web3, deploy_address):
            # Deploy can last max 1 h
            request_account_unlock(chain, deploy_address, timeout=3600)

    # Use non-default gas price for speedier processing
    gas_price = int(web3.eth.gasPrice * 2)

    transaction = {"from": deploy_address, "gasPrice": gas_price}
    kwargs = dict(**contract_def["arguments"])  # Unwrap YAML CommentedMap

    print("Starting", contract_name, "deployment, with arguments ", kwargs, "gas price is", gas_price / (10**9), "GWei")

    # TODO: Workaround when deploying the same contract twice in run,
    # because Populus contract_identity allows only one contract_identity per contract class
    if "JSONFile" in chain.registrar.registrar_backends:
        del chain.registrar.registrar_backends["JSONFile"]
    chain.registrar.registrar_backends["Memory"].contract_addresses = defaultdict(set)

    try:
        contract, txhash = chain.provider.deploy_contract(contract_name, deploy_transaction=transaction, deploy_kwargs=kwargs)
    except Exception as e:
        raise RuntimeError("Could not deploy contract {}, constructor arguments {}".format(contract_name, kwargs)) from e

    contract_def["address"] = contract.address
    print(contract_name, "address is", contract.address)

    constructor_args = get_constructor_arguments(contract, kwargs=kwargs)
    print(contract_name, "constructor arguments payload is", constructor_args)
    contract_def["constructor_args"] = constructor_args

    libraries = get_libraries(chain, contract_name, contract)
    print(contract_name, "libraries are", libraries)
    contract_def["libraries"] = libraries

    return contract


def deploy_crowdsale(project: Project, chain, yaml_filename: str, source_definitions: dict, deploy_address) -> Tuple[dict, dict, dict]:
    """Deploy multiple contracts from crowdsale definitions.

    :param chain: Populus chain object
    :param data: One of mainnet/ropsten parsed data definitions in a YAML file
    :return: Tuple (expaneded definitions, statistics, contract object map). The expanded definitions are run-time data that has everything expanded out and actual contract addresses
    """

    statistics = Counter()

    # This will contain our output and parsed values
    runtime_data = copy.deepcopy(source_definitions)

    # Contract handles for post-actions
    contracts = {}

    # Store the address we used for the deployment
    runtime_data["deploy_address"] = deploy_address
    chain_name = runtime_data["chain"]
    verify_on_etherscan = asbool(runtime_data["verify_on_etherscan"])
    browser_driver = runtime_data.get("browser_driver", "chrome")
    solc = runtime_data.get("solc")

    need_unlock = runtime_data.get("unlock_deploy_address", True)

    for name, contract_def in runtime_data["contracts"].items():

        contract_name = contract_def["contract_name"]

        # First expand out all variables
        address = contract_def.get("address")
        if address:
            print("Already deployed contract,", name, address)
            Contract = get_contract_by_name(chain, contract_name)
            contracts[name] = Contract(address=address)
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

        contracts[name] = deploy_contract(project, chain, deploy_address, expanded_contract_def, chain_name, need_unlock=need_unlock)
        statistics["deployed"] += 1

        # Perform manual verification of the deployed contract
        if verify_on_etherscan:
            fname = runtime_data["contracts"][name]["contract_file"]
            src = verify_contract(
                project=project,
                chain_name=chain_name,
                address=runtime_data["contracts"][name]["address"],
                contract_name=contract_name,
                contract_filename=fname,
                constructor_args=runtime_data["contracts"][name]["constructor_args"],
                libraries=runtime_data["contracts"][name]["libraries"],
                browser_driver=browser_driver,
                compiler=solc["version"],
                optimization=asbool(solc["optimizations"]["optimizer"]),
                optimizer_runs=int(solc["optimizations"]["runs"])
            )
            runtime_data["contracts"][name]["etherscan_link"] = get_etherscan_link(chain_name, runtime_data["contracts"][name]["address"])

            # Write out our expanded contract
            expanded_path = os.path.join(os.getcwd(), "build", "expanded", fname)
            with open(expanded_path, "wt") as out:
                out.write(src)

        # Write the ongoing output, so we can use it e.g. to debug EtherScan verification
        write_deployment_report(yaml_filename, runtime_data, partial=True)

    return runtime_data, statistics, contracts


def write_deployment_report(yaml_filename: str, runtime_data: dict, partial=False):
    """Write run-time data to a result file, so that it can easily inspected and shared.

    :param partial: Don't override existing successful deployment report by accident
    """

    partial_report_filename = yaml_filename.replace(".yml", ".partial-report.yml")

    if partial:
        report_filename = partial_report_filename
        print("Writing partial report", report_filename)
    else:
        report_filename = yaml_filename.replace(".yml", ".deployment-report.yml")

    with open(report_filename, "wt") as out:
        out.write(ruamel.yaml.round_trip_dump(runtime_data))

    if not partial:
        # Delete the partial file name after successfully deploying everything
        if os.path.exists(partial_report_filename):
            os.unlink(partial_report_filename)


def exec_lines(lines: str, context: dict, print_prefix=None):
    """Exec python code line-by-line and stop on error.
    :param lines: Python code snippet to evaluate
    :param context: Evaluation context
    :param print_prefix: Echo all lines we evaluate
    """

    buffer = ""

    for line in lines.split("\n"):

        if not line.strip():
            continue

        line = line.strip()

        if line.endswith("\\"):
            buffer += line.strip("\\")
            continue
        else:
            buffer += line

        if print_prefix:
            print(print_prefix, buffer)
        try:
            exec(buffer, context)
        except Exception as e:
            raise RuntimeError("Failed when running: {}".format(buffer)) from e

        buffer = ""


def perform_post_actions(chain, runtime_data: dict, contracts: dict):
    """Make contracts to set up call chains."""

    web3 = chain.web3

    post_actions = runtime_data.get("post_actions")
    if post_actions:
        context = get_post_actions_context(post_actions, runtime_data, contracts, web3)
        post_actions = textwrap.dedent(post_actions)

        print("Performing post-deployment contract actions")
        exec_lines(post_actions, context, print_prefix="Action:")
    else:
        print("No post-deployment actions defined")


def perform_verify_actions(chain, runtime_data: dict, contracts: dict):
    """Check out deployment was solid."""

    web3 = chain.web3

    verify_actions = runtime_data.get("verify_actions")
    if verify_actions:
        context = get_post_actions_context(verify_actions, runtime_data, contracts, web3)

        verify_actions = textwrap.dedent(verify_actions)
        print("Performing deployment verification")

        # Allow some time for post_actions to be mined
        time.sleep(60)

        exec_lines(verify_actions, context, print_prefix="Verification:")
    else:
        print("No verify defined")



def _deploy_contracts(project, chain, web3, yaml_filename, chain_data, deploy_address):
    """Kernel for deploing contracts."""

    # Coinbase aliasing
    if deploy_address == "coinbase":
        deploy_address = web3.eth.accounts[0]

    address = deploy_address
    print("Web3 provider is", web3.currentProvider)
    print("Owner address is", address)
    start_balance = from_wei(web3.eth.getBalance(address), "ether")
    print("Owner balance is", start_balance, "ETH")

    runtime_data, statistics, contracts = deploy_crowdsale(project, chain, yaml_filename, chain_data, deploy_address)
    perform_post_actions(chain, runtime_data, contracts)
    perform_verify_actions(chain, runtime_data, contracts)
    write_deployment_report(yaml_filename, runtime_data)
    end_balance = from_wei(web3.eth.getBalance(address), "ether")
    print("Deployment cost is", start_balance - end_balance, "ETH")
    return runtime_data, statistics, contracts


def deploy_crowdsale_from_file(project: Project, yaml_filename: str, deployment_name: str, deploy_address: str):
    """Deploy crowdsale plan."""

    if not yaml_filename.endswith(".yml"):
        # A stop gap fix
        # Otherwise our backup filename generator may get confused
        raise RuntimeError("YAML files must have .yml extension")

    chain_data = load_crowdsale_definitions(yaml_filename, deployment_name)
    chain_name = chain_data["chain"]

    with project.get_chain(chain_name) as chain:
        web3 = chain.web3
        return _deploy_contracts(project, chain, web3, yaml_filename, chain_data, deploy_address)


