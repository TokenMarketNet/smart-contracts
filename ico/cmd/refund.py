"""Distribute ETH refunds."""
import csv
import datetime
import json
import os
import time
from decimal import Decimal
import shutil

import click
from eth_utils import from_wei
from eth_utils import to_wei

from populus.utils.accounts import is_account_locked
from populus import Project
from populus.utils.cli import request_account_unlock

from ico.utils import check_succesful_tx



@click.command()
@click.option('--chain', nargs=1, default="mainnet", help='On which chain to deploy - see populus.json')
@click.option('--hot-wallet-address', nargs=1, help='The account that deploys the issuer contract, controls the contract and pays for the gas fees', required=True)
@click.option('--csv-file', nargs=1, help='CSV file containing distribution data', required=True)
@click.option('--address-column', nargs=1, help='Name of CSV column containing Ethereum addresses', default="address")
@click.option('--amount-column', nargs=1, help='Name of CSV column containing decimal token amounts', default="amount")
@click.option('--id-column', nargs=1, help='Name of CSV column containing unique identifier for all refund participants (usually email)', default="email")
@click.option('--limit', nargs=1, help='How many items to import in this batch', required=False, default=1000)
@click.option('--start-from', nargs=1, help='First row to import (zero based)', required=False, default=0)
@click.option('--state-file', nargs=1, help='JSON file where we keep the state', required=True)
def main(chain, hot_wallet_address, csv_file, limit, start_from, address_column, amount_column, id_column, state_file):
    """Distribute ETh refunds.

    Reads in funds distribution data as CSV. Then sends funds from a local address.

    The refund status is stored as a JSON file.

    Example:

        refund --chain=kovan --hot-wallet-address=0x001fc7d7e506866aeab82c11da515e9dd6d02c25 --csv-file=refunds.csv --address-column="Refund address" --amount-column="ETH" --id-column="Email" --start-from=0 --limit=2 --state-file=refund-state.json

    Example CSV data:

    .. code-block:: csv

        Email,ETH,Refund address
        yyy@xxx.com,61.52,0x0e78EF811B6564c996fD10012579633B1a518b9D
        yyy@xxx.com,111.21,0xf0b91641CCe2ADB4c0D7B90c54E7eE96CCCBc3d1
        yyy@xxx.com,61.52,0x5dAbC71Faa8982bF23eE2c4979d22536F5101065
        yyy@xxx.com,61.52,0x9B8EceBc18153166Beec1b568D510B55B560789D
    """

    # Make a backup of the state file
    if os.path.exists(state_file):
        assert state_file.endswith(".json")
        backup_name = state_file.replace(".json", datetime.datetime.utcnow().isoformat() + ".bak.json")
        print("Backing up state file to", backup_name)
        shutil.copy(state_file, backup_name)

    project = Project()

    with project.get_chain(chain) as c:

        web3 = c.web3
        print("Web3 provider is", web3.currentProvider)
        print("Hot wallet address is", hot_wallet_address)
        print("Hot wallet balance is", from_wei(web3.eth.getBalance(hot_wallet_address), "ether"), "ETH")

        # Goes through geth account unlock process if needed
        if is_account_locked(web3, hot_wallet_address):
            request_account_unlock(c, hot_wallet_address, timeout=3600*6)
            assert not is_account_locked(web3, hot_wallet_address)

        print("Reading data", csv_file)
        with open(csv_file, "rt") as inp:
            reader = csv.DictReader(inp)
            rows = [row for row in reader]

        # Check that we have unique addresses
        uniq_ids = set()
        for row in rows:
            id = row[id_column].strip()
            if id in uniq_ids:
                raise RuntimeError("Id appears twice in input data", id)
            uniq_ids.add(id)

        # Start distribution
        start_time = time.time()
        start_balance = from_wei(web3.eth.getBalance(hot_wallet_address), "ether")

        print("Total rows", len(rows))

        if os.path.exists(state_file):
            with open(state_file, "rt") as inp:
                state = json.load(inp)
        else:
            state = {}

        for i in range(start_from, min(start_from+limit, len(rows))):
            data = rows[i]
            addr = data[address_column].strip()
            id = data[id_column].strip()
            amount = Decimal(data[amount_column].strip())
            amount_wei = to_wei(amount, "ether")

            if id in state:
                print("Already refunded", id, addr, amount)
                continue

            # Use non-default gas price for speedier processing
            gas_price = int(web3.eth.gasPrice * 1.2)

            txid = web3.eth.sendTransaction({"from": hot_wallet_address, "to": addr, "value": amount_wei, "gasPrice": gas_price})
            duration = time.time() - start_time
            print("Transferring", id, amount_wei, "to", addr, "txid", txid, "duration", duration)

            state[id] = txid
            with open(state_file, "wt") as out:
                json.dump(state, out)

            check_succesful_tx(web3, txid)

        end_balance = from_wei(web3.eth.getBalance(hot_wallet_address), "ether")
        print("Deployment cost is", start_balance - end_balance, "ETH")
        print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
