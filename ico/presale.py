"""Deploy pre-sale contract."""
import click

import time

import sys
from eth_utils import from_wei
from eth_utils import to_wei
from populus.utils.accounts import is_account_locked

from populus import Project
from populus.utils.cli import request_account_unlock


@click.command()
@click.option('--chain', nargs=1, default="mainnet", help='On which chain to deploy')
@click.option('--address', nargs=1, help='Account to deploy from (must exist on geth)', default=None)
@click.option('--days', nargs=1, default=30, help='How many days presale is frozen for', type=int)
@click.option('--minimum', nargs=1, default=1, help='What is the minimum pre-ico buy in (ether)', type=float)
def main(chain, address, days, minimum):

    project = Project()

    minimum = to_wei(minimum, "ether")
    freeze_ends_at = time.time() + days * 24*3600

    # This is configured in populus.json
    # We are working on a testnet
    print("Make sure {} chain is running, you can connect to it, or you'll get timeout".format(chain))

    with project.get_chain(chain) as c:

        web3 = c.web3
        print("Web3 provider is", web3.currentProvider)
        print("Deploy address is", address)
        if not address:
            sys.exit("You need to explicitly give the address from where we are deploying from")

        print("Deploy address balance is", from_wei(web3.eth.getBalance(address), "ether"))

        # Goes through geth account unlock process if needed
        if is_account_locked(web3, address):
            request_account_unlock(c, address, None)

        transaction = {"from": address}
        args = [freeze_ends_at, minimum]

        # This does deployment with all dependencies linked in
        presale, txhash = chain.provider.deploy_contract('PresaleFundCollector', deploy_transaction=transaction, deploy_args=args)
        print("Deploying presale, tx hash is", txhash)
        print("Presale contract address is", presale.address)

        # Do some contract reads to see everything looks ok
        print("Presale freeze ends at", presale.call().freezeEndsAt())
        print("Presale minimum buy in (wei) is", presale.call().weiMinimumLimit())

        # Estimate invest() gas cost
        estimation = presale.estimateGas(tranaction={"from": address, "value": to_wei(1000, "ether")}}).invest()

        print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
