"""Reclaim tokens for payments that failed checks before the token release ."""
import logging

import click

from eth_utils import from_wei
from populus.utils.accounts import is_account_locked
from populus import Project
from populus.utils.cli import request_account_unlock

from ico.logging import setup_console_logging
from ico.amlreclaim import prepare_csv
from ico.amlreclaim import count_tokens_to_reclaim, reclaim_all


@click.command()
@click.option('--chain', nargs=1, default="mainnet", help='On which chain to deploy - see populus.json')
@click.option('--owner-address', nargs=1, help='The token owner address. Must be an unlocked Ethereum account at your Ethereum node')
@click.option('--token', nargs=1, help='Token contract address', required=True)
@click.option('--csv-file', nargs=1, help='CSV file containing distribution data', required=True)
@click.option('--address-column', nargs=1, help='Name of CSV column containing Ethereum addresses', default="address")
@click.option('--label-column', nargs=1, help='Name of CSV column containing label for addresses', default="label")
@click.option('--gas-price', nargs=1, help='Gas price in GWei to used for the transactions')
def main(chain, owner_address, token, csv_file, address_column, label_column, gas_price):
    """Reclaim tokens that failed AML check.

    Before the token release, after AML/post sale KYC data has been assembled, go through the addresses that failed the checks and get back tokens from those buyers.

    Owner account must have balance to perform the the reclaim transactions.

    Example:

        aml-reclaim \
          --token=0x... \
          --owner-address=0x... \
          --address-column="address" \
          --label-column="label" \
          --csv-file=test.csv
    """

    setup_console_logging()

    logger = logging.getLogger(__name__)

    project = Project()

    with project.get_chain(chain) as c:

        web3 = c.web3
        logger.info("Web3 provider is %s", web3.currentProvider)
        logger.info("Owner account address is %s", owner_address)
        logger.info("Owner account balance is %s ETH", from_wei(web3.eth.getBalance(owner_address), "ether"))

        # Goes through geth account unlock process if needed
        if is_account_locked(web3, owner_address):
            request_account_unlock(c, owner_address, timeout=3600*6)
            assert not is_account_locked(web3, owner_address)

        Token = c.provider.get_base_contract_factory('AMLToken')
        token = Token(address=token)

        logger.info("Token address is %s", token.address)

        decimals = token.call().decimals()
        logger.info("Total supply is %s", token.call().totalSupply() / (10**decimals))
        logger.info("Owner account token balance is", token.call().balanceOf(owner_address))

        if gas_price:
            gas_price = int(gas_price) * 10**9
        else:
            # Use default gas price with little multiplies to cut us at the front of the queue
            gas_price = web3.eth.gasPrice * 1.2

        tx_params = {
            "from": owner_address,
            "gasPrice": gas_price,
        }

        logger.info("Using gas price of %f", gas_price / 10**9, "GWei")

        logger.info("Reading data from %s", csv_file)
        with open(csv_file, "rt") as inp:
            rows = prepare_csv(inp, address_column, label_column)

        amount = count_tokens_to_reclaim(token, rows) / 10**decimals
        logger.info("Claiming total %f tokens", amount)

        start_balance = from_wei(web3.eth.getBalance(owner_address), "ether")
        reclaim_all(token, rows, tx_params)

        end_balance = from_wei(web3.eth.getBalance(owner_address), "ether")
        logger.info("Deployment cost is %f ETH", start_balance - end_balance)
        logger.info("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
