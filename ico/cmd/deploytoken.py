"""Deploy tokens contract."""
import os
import time
import sys
import datetime

import click
from eth_utils import from_wei
from eth_utils import to_wei
from populus.utils.accounts import is_account_locked
from populus import Project
from populus.utils.cli import request_account_unlock

from ico.utils import check_succesful_tx
from ico.utils import get_constructor_arguments
from ico.etherscan import verify_contract
from ico.etherscan import get_etherscan_link


@click.command()
@click.option('--chain', nargs=1, default="mainnet", help='On which chain to deploy - see populus.json')
@click.option('--address', nargs=1, help='Address to deploy from and who becomes as a owner (must exist on geth)', required=True)
@click.option('--contract-name', nargs=1, help='Name of the token contract', default="CentrallyIssuedToken")
@click.option('--release-agent', nargs=1, help='Address that acts as a release agent (can be same as owner)', default=None)
@click.option('--minting-agent', nargs=1, help='Address that acts as a minting agent (can be same as owner)', default=None)
@click.option('--name', nargs=1, required=True, help='Token name', type=str)
@click.option('--symbol', nargs=1, required=True, help='Token symbol', type=str)
@click.option('--supply', nargs=1, default=21000000, help='What is the initial token supply', type=int)
@click.option('--decimals', nargs=1, default=0, help='How many decimal points the token has', type=int)
@click.option('--verify/--no-verify', default=False, help='Verify contract on EtherScan.io')
@click.option('--verify-filename', nargs=1, help='Solidity source file of the token contract for verification', default=None)
def main(chain, address, contract_name, name, symbol, supply, decimals, minting_agent, release_agent, verify, verify_filename):
    """Deploy a token contract.

    Examples:

    deploy-token --chain=ropsten --address=0x3c2d4e5eae8c4a31ccc56075b5fd81307b1627c6 --name="MikkoToken 2.0" --symbol=MOO --release-agent=0x3c2d4e5eae8c4a31ccc56075b5fd81307b1627c6  --supply=100000

    deploy-token --chain=kovan --contract-name="CentrallyIssuedToken" --address=0x001FC7d7E506866aEAB82C11dA515E9DD6D02c25  --name="TestToken" --symbol=MOO --supply=916 --decimals=0 --verify --verify-filename=CentrallyIssuedToken.sol
    """

    project = Project()

    with project.get_chain(chain) as c:

        web3 = c.web3
        print("Web3 provider is", web3.currentProvider)
        print("Owner address is", address)
        print("Owner balance is", from_wei(web3.eth.getBalance(address), "ether"), "ETH")

        # Goes through geth account unlock process if needed
        if is_account_locked(web3, address):
            request_account_unlock(c, address, None)

        transaction = {"from": address}
        args = [name, symbol, supply, decimals]

        if contract_name == "CentrallyIssuedToken":
            # TODO: Generalize settings contract args
            # This sets the upgrade master
            args = [address] + args

        # This does deployment with all dependencies linked in

        print("Starting contract deployment")
        contract, txhash = c.provider.deploy_contract(contract_name, deploy_transaction=transaction, deploy_args=args)
        print("Contract address is", contract.address)

        # This is needed for Etherscan contract verification
        # https://etherscanio.freshdesk.com/support/solutions/articles/16000053599-contract-verification-constructor-arguments
        const_args = get_constructor_arguments(contract, args)
        print("CrowdsaleToken constructor arguments is", const_args)

        if release_agent:
            print("Setting release agent to", release_agent)
            txid = contract.transact(transaction).setReleaseAgent(release_agent)
            check_succesful_tx(web3, txid)

        if minting_agent:
            print("Setting minting agent")
            txid = contract.transact(transaction).setMintAgent(minting_agent, True)
            check_succesful_tx(web3, txid)

        if verify:
            chain_name = chain
            fname = verify_filename
            browser_driver = "chrome"
            verify_contract(
                project=project,
                libraries={},  # TODO: Figure out how to pass around
                chain_name=chain_name,
                address=contract.address,
                contract_name=contract_name,
                contract_filename=fname,
                constructor_args=const_args,
                # libraries=runtime_data["contracts"][name]["libraries"],
                browser_driver=browser_driver)
            link = get_etherscan_link(chain_name, contract.address)

            print("Verified contract is", link)

        # Do some contract reads to see everything looks ok
        try:
            print("Token owner:", contract.call().owner())
        except ValueError:
            pass  # No owner

        try:
            print("Token upgradeMaster:", contract.call().upgradeMaster())
        except ValueError:
            pass

        try:
            print("Token minting finished:", contract.call().mintingFinished())
        except ValueError:
            pass

        try:
            print("Token released:", contract.call().released())
            print("Token release agent:", contract.call().releaseAgent())
        except ValueError:
            pass

        print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
