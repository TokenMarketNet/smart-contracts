"""Deploy pre-sale contract."""
import time
import sys
import datetime

import click
from eth_utils import from_wei
from eth_utils import to_wei
from populus.utils.accounts import is_account_locked
from populus import Project
from populus.utils.cli import request_account_unlock

from ico.utils import get_constructor_arguments
from ico.utils import get_libraries
from ico.etherscan import verify_contract


def utc_time():
    """UTC UNIX time.

    http://stackoverflow.com/a/22101249/315168
    """
    d = datetime.datetime.utcnow()
    epoch = datetime.datetime(1970, 1, 1)
    t = (d - epoch).total_seconds()
    return t


@click.command()
@click.option('--chain', nargs=1, default="mainnet", help='On which chain to deploy - see populus.json')
@click.option('--address', nargs=1, help='Account to deploy from. Must exist on geth.', required=True)
@click.option('--owner', nargs=1, help='Address that is set as owner of the presale contract', required=True)
@click.option('--days', nargs=1, default=30, help='How many days presale is frozen for', type=int)
@click.option('--minimum', nargs=1, default=1, help='What is the minimum pre-ico buy in (ether)', type=float)
@click.option('--verify/--no-verify', default=False, help='Verify contract source code one EtherScan.io')
def main(chain, address, owner, days, minimum, verify):
    """Deploy a PresaleFundCollector contract.

    Example:

     deploy-presale --chain=ropsten --address=0x3c2d4e5eae8c4a31ccc56075b5fd81307b1627c6  --owner=0x3c2d4e5eae8c4a31ccc56075b5fd81307b1627c6 --days=30 --minimum=30

    """
    project = Project()

    # Parse command line args to presale constructor args
    minimum = to_wei(minimum, "ether")
    freeze_ends_at = int(utc_time() + days * 24*3600)

    contract_name = "PresaleFundCollector"

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
        args = [owner, freeze_ends_at, minimum]

        # This does deployment with all dependencies linked in
        print("Deploying contracts")
        presale, txhash = c.provider.deploy_contract(contract_name, deploy_transaction=transaction, deploy_args=args)
        print("Deploying presale, tx hash is", txhash)
        print("Presale contract address is", presale.address)

        libraries = get_libraries(c, contract_name, presale)
        print("Linked libraries are", libraries)

        # This is needed for Etherscan contract verification
        # https://etherscanio.freshdesk.com/support/solutions/articles/16000053599-contract-verification-constructor-arguments
        constructor_args = get_constructor_arguments(presale, args)
        print("Presale constructor arguments is", constructor_args)

        if verify:
            print("Verifying contract")
            verify_contract(
                project=project,
                chain_name=chain,
                address=presale.address,
                contract_name="PresaleFundCollector",
                contract_filename="PresaleFundCollector.sol",
                constructor_args=constructor_args,
                libraries=libraries)


        # Do some contract reads to see everything looks ok
        print("Presale freeze ends at", presale.call().freezeEndsAt())
        print("Presale minimum buy in (wei) is", presale.call().weiMinimumLimit())

        # Estimate invest() gas cost
        estimation = presale.estimateGas(transaction={"from": address, "value": to_wei(1000, "ether")}).invest()
        print("Presale.invest() estimated gas cost is", estimation)

        sig_data = presale._prepare_transaction("invest")
        print("Presale.invest() data payload is", sig_data["data"])

        sig_data = presale._prepare_transaction("refund")
        print("Presale.refund() data payload is", sig_data["data"])

        print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
