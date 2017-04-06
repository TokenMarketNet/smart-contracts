"""Deploy tokens contract."""
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


@click.command()
@click.option('--chain', nargs=1, default="mainnet", help='On which chain to deploy - see populus.json')
@click.option('--address', nargs=1, help='Address to deploy from and who becomes as a owner (must exist on geth)', required=True)
@click.option('--release-agent', nargs=1, help='Address that acts as a release agent (can be same as owner)', default=None)
@click.option('--minting-agent', nargs=1, help='Address that acts as a minting agent (can be same as owner)', default=None)
@click.option('--name', nargs=1, required=True, help='How many days presale is frozen for', type=str)
@click.option('--symbol', nargs=1, required=True, help='What is the minimum pre-ico buy in (ether)', type=str)
@click.option('--supply', nargs=1, default=21000000, help='What is the minimum pre-ico buy in (ether)', type=int)
def main(chain, address, name, symbol, supply, minting_agent, release_agent):
    """Deploy a CrowdsaleToken contract.

    Example:

    deploy-token --chain=ropsten --address=0x3c2d4e5eae8c4a31ccc56075b5fd81307b1627c6 --name="MikkoToken 2.0" --symbol=MOO --release-agent=0x3c2d4e5eae8c4a31ccc56075b5fd81307b1627c6  --supply=100000

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
        args = [name, symbol, supply]

        # This does deployment with all dependencies linked in

        print("Starting contract deployment")
        contract, txhash = c.provider.deploy_contract('CrowdsaleToken', deploy_transaction=transaction, deploy_args=args)
        print("Contract address is", contract.address)

        # This is needed for Etherscan contract verification
        # https://etherscanio.freshdesk.com/support/solutions/articles/16000053599-contract-verification-constructor-arguments
        data = get_constructor_arguments(contract, args)
        print("CrowdsaleToken constructor arguments is", data)

        if release_agent:
            print("Setting release agent to", release_agent)
            txid = contract.transact(transaction).setReleaseAgent(release_agent)
            check_succesful_tx(web3, txid)

        if minting_agent:
            print("Setting minting agent")
            txid = contract.transact(transaction).setMintAgent(minting_agent, True)
            check_succesful_tx(web3, txid)

        # Do some contract reads to see everything looks ok
        print("Token owner:", contract.call().owner())
        print("Token minting finished:", contract.call().mintingFinished())
        print("Token released:", contract.call().released())
        print("Token release agent:", contract.call().releaseAgent())

        print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
