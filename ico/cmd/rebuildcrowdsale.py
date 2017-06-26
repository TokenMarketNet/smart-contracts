"""Deploy tokens contract."""
import csv
import time
import sys
import datetime

import click
from decimal import Decimal
from eth_utils import from_wei
from eth_utils import to_wei
from populus.utils.accounts import is_account_locked
from populus import Project
from populus.utils.cli import request_account_unlock

from ico.utils import check_succesful_tx
from ico.utils import check_multiple_succesful_txs
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
    """Rebuild data on relaunched CrowdsaleToken contract.

    This allows you rerun investment data to fix potential errors in the contract.

    Example::

        rebuild-crowdsale --address=0x001FC7d7E506866aEAB82C11dA515E9DD6D02c25  --chain=kovan --contract-address=0xf09e4a27a02afd29590a989cb2dda9af8eebc77f --start-from=0 --limit=600 --multiplier=12 --csv-file=inputdata.csv


        rebuild-crowdsale --address=0x001FC7d7E506866aEAB82C11dA515E9DD6D02c25  --chain=kovan --contract-address=0xf09e4a27a02afd29590a989cb2dda9af8eebc77f --start-from=0 --limit=600 --multiplier=12 --csv-file=inputdata.csv

    """

    project = Project()

    with project.get_chain(chain) as c:

        web3 = c.web3
        print("Web3 provider is", web3.currentProvider)
        print("Owner address is", address)
        print("Owner balance is", from_wei(web3.eth.getBalance(address), "ether"), "ETH")

        # Goes through geth account unlock process if needed
        if is_account_locked(web3, address):
            request_account_unlock(c, address, timeout=3600*6)

        print("Reading data", csv_file)
        with open(csv_file, "rt") as inp:
            reader = csv.DictReader(inp)
            rows = [row for row in reader]

        print("Source data has", len(rows), "rows")
        print("Importing rows", start_from, "-", start_from + limit)

        RelaunchedCrowdsale = c.provider.get_base_contract_factory('RelaunchedCrowdsale')
        relaunched_crowdsale = RelaunchedCrowdsale(address=contract_address)

        print("Crowdsale contract is", contract_address)
        print("Currently issued", relaunched_crowdsale.call().tokensSold())

        assert relaunched_crowdsale.call().owner().lower() == address.lower(), "We are not the crowdsale owner. Real owner is {}, we are {}".format(relaunched_crowdsale.call().owner(), address)

        multiplier = 10**multiplier

        start_time = time.time()
        start_balance = from_wei(web3.eth.getBalance(address), "ether")

        tx_to_confirm = []   # List of txids to confirm
        tx_batch_size = 16  # How many transactions confirm once
        cap_check = True

        for i in range(start_from, min(start_from+limit, len(rows))):
            data = rows[i]
            addr = data["Address"]
            wei = to_wei(data["Invested ETH"], "ether")
            fractional_tokens = Decimal(data["Received tokens"])
            orig_txid = int(data["Tx hash"], 16)
            # orig_tx_index = int(data["Tx index"])

            tokens = fractional_tokens * multiplier

            transaction = {
                "from": address,
                "gasPrice": int(web3.eth.gasPrice * 1.2)
            }

            # 40 GWei should be the low
            if transaction["gasPrice"] < 35 * 10**9:
                print("Got lowish gas price: {}".format(transaction))
                transaction["gasPrice"] = 35 * 10**9

            # http://stackoverflow.com/a/19965088/315168
            if not tokens % 1 == 0:
                raise RuntimeError("Could not issue tokens because after multiplication was not integer: {} {} {}".format(tokens, fractional_tokens, multiplier))

            end_balance = from_wei(web3.eth.getBalance(address), "ether")
            spent = start_balance - end_balance
            print("Row", i,  "giving", tokens, "to", addr, "from tx", orig_txid, "ETH spent", spent, "time passed", time.time() - start_time)

            if relaunched_crowdsale.call().getRestoredTransactionStatus(orig_txid):
                print("Already restored, skipping")
                continue

            tokens = int(tokens)

            if cap_check:
                # See if our cap calculation is screwed
                if relaunched_crowdsale.call().isBreakingCap(wei, tokens, relaunched_crowdsale.call().weiRaised(), relaunched_crowdsale.call().tokensSold()):
                    raise RuntimeError("Cap error")

            txid = relaunched_crowdsale.transact(transaction).setInvestorDataAndIssueNewToken(addr, wei, tokens, orig_txid)
            tx_to_confirm.append(txid)

            # Confirm N transactions when batch max size is reached
            if len(tx_to_confirm) >= tx_batch_size:
                check_multiple_succesful_txs(web3, tx_to_confirm)
                tx_to_confirm = []

        # Confirm dangling transactions
        check_multiple_succesful_txs(web3, tx_to_confirm)

        end_balance = from_wei(web3.eth.getBalance(address), "ether")
        print("Deployment cost is", start_balance - end_balance, "ETH")
        print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
