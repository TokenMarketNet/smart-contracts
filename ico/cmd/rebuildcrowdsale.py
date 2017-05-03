"""Deploy tokens contract."""
import csv
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
@click.option('--address', nargs=1, help='Owner account (must exist on Ethereum node)', required=True)
@click.option('--contract-address', nargs=1, help='RebuildCrowdsale contract address', required=True)
@click.option('--csv-file', nargs=1, help='CSV export of existing data created with extract-raw-investment-data ', required=True)
@click.option('--limit', nargs=1, help='How many items to import in this batch', required=False, default=1000)
@click.option('--start-from', nargs=1, help='First row to import (zero based)', required=False, default=0)
@click.option('--multiplier', nargs=1, help='Token amount multiplier, to fix decimal place, as 10^exponent', required=False, default=1)
def main(chain, address, contract_address, csv_file, limit, start_from, multiplier):
    """Rebuild a relaunched CrowdsaleToken contract.

    Example:
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

        print("Reading data", csv_file)
        with open(csv_file, "rt") as inp:
            reader = csv.DictReader(inp)
            rows = [row for row in reader]

        print("Source data has", len(rows), "rows")
        print("Importing rows", start_from, "-", start_from + limit)

        RelaunchedCrowdsale = c.provider.get_contract_factory('RelaunchedCrowdsale')
        relaunched_crowdsale = RelaunchedCrowdsale(address=contract_address)
        print("Crowdsale contract is", contract_address)
        print("Currently issued", relaunched_crowdsale.call().tokensSold())

        assert relaunched_crowdsale.call().owner().lower() == address.lower(), "We are not the crowdsale owner. Real owner is {}, we are {}".format(relaunched_crowdsale.call().owner(), address)

        multiplier = 10**multiplier

        start_balance = from_wei(web3.eth.getBalance(address), "ether")
        for i in range(start_from, start_from+limit):
            data = rows[i]
            addr = data["Address"]
            wei = to_wei(data["Invested ETH"], "ether")
            tokens = int(data["Received tokens"])
            orig_txid = int(data["Tx hash"], 16)
            orig_tx_index = int(data["Tx index"])

            tokens *= multiplier
            print("Row", i,  "giving", tokens, "to", addr, "from tx", orig_txid, "#", orig_tx_index)

            if relaunched_crowdsale.call().getRestoredTransactionStatus(orig_txid, orig_tx_index):
                print("Already restored, skipping")
                continue

            raised = relaunched_crowdsale.call().weiRaised()
            sold = relaunched_crowdsale.call().tokensSold()
            if relaunched_crowdsale.call().isBreakingCap(tokens, wei, raised, sold):
                sys.exit("Oops broke the cap.")

            txid = relaunched_crowdsale.transact(transaction).setInvestorDataAndIssueNewToken(addr, wei, tokens, orig_txid, orig_tx_index)
            check_succesful_tx(web3, txid)

        end_balance = from_wei(web3.eth.getBalance(address), "ether")
        print("Deployment cost is", start_balance - end_balance, "ETH")
        print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
