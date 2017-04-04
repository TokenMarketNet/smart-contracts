"""Deploy a multisig wallet contract."""

import click
from eth_utils import from_wei
from populus.utils.accounts import is_account_locked
from populus import Project
from populus.utils.cli import request_account_unlock

from ico.utils import get_constructor_arguments


@click.command()
@click.option('--chain', nargs=1, default="mainnet", help='On which chain to deploy - see populus.json')
@click.option('--address', nargs=1, help='Address to deploy from and who becomes as a owner (must exist on geth). This will become automatically one of cosigners.', required=True)
@click.option('--cosigners', nargs=1, required=True, help='Comma separated list of addresses that are the multisig wallet cosigners')
@click.option('--required', nargs=1, required=True, help='How many cosigners are required for a transaction', type=int)
def main(chain, address, cosigners, required):
    """Deploy a multisig wallet contract.

    Example of creating a multisig wallet with 2/3 cosigners required:

    deploy-multisig --chain=ropsten --address=0x3c2d4e5eae8c4a31ccc56075b5fd81307b1627c6  --cosigners=0xa5384627F6DcD3440298E2D8b0Da9d5F0FCBCeF7,0xD947F285Dbf2098C248133209cb92343e44e9BA8 --required=2
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

        cosigners = cosigners.split(",")
        args = [cosigners, required, 0]

        # This does deployment with all dependencies linked in

        print("Starting contract deployment")

        # This will giv you TypeError: One or more arguments could not be encoded to the necessary ABI type if any of the addresses is not valid
        contract, txhash = c.provider.deploy_contract('Wallet', deploy_transaction=transaction, deploy_args=args)
        print("Contract address is", contract.address)

        # This is needed for Etherscan contract verification
        # https://etherscanio.freshdesk.com/support/solutions/articles/16000053599-contract-verification-constructor-arguments
        data = get_constructor_arguments(contract, args)
        print("Contract constructor arguments is", data)

        # Do some contract reads to see everything looks ok
        for i in range(0, 10):
            owner = contract.call().getOwner(i)

            if owner == "0x0000000000000000000000000000000000000000":
                # EVM gives you null value if you do array out of bounds
                break

            print("Wallet cosigner #{}:".format(i+1), owner)
            if owner == "0x0":
                break

        print("Number of cosigners required for execution:", contract.call().m_required())
        print("Wallet balance:", web3.eth.getBalance(contract.address))
        print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
