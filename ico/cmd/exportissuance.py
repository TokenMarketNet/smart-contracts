import csv
import datetime
import json
import os

import click
from decimal import Decimal
from eth_utils import from_wei
from populus import Project


@click.command()
@click.option('--chain', nargs=1, default="mainnet", help='On which chain to deploy - see populus.json')
@click.option('--address', nargs=1, help='CrowdsaleContract address to scan', required=True)
@click.option('--csv-file', nargs=1, help='CSV file to write', default=None, required=True)
def main(chain, address, csv_file):
    """Export issued events.

    Build a CSV file of run centralized token distribution. This can be later used to tell users what TXID gave them their tokens if we know the external id of the user.

    Example:

        export-issuance \
            --address=0x0.... \
            --csv-file=issued-test-drop.csv \
            --chain=mainnet

    """

    project = Project()
    timestamp_filename = "block-timestamps.json"

    with project.get_chain(chain) as c:

        web3 = c.web3
        print("Web3 provider is", web3.currentProvider)
        # Sanity check
        print("Block number is", web3.eth.blockNumber)

        IssuerWithId = c.provider.get_base_contract_factory('IssuerWithId')
        contract = IssuerWithId(address=address)

        CentrallyIssuedToken = c.provider.get_base_contract_factory('CentrallyIssuedToken')
        token = CentrallyIssuedToken(address=contract.functions.token().call())

        decimals = token.functions.decimals().call()
        decimal_multiplier = 10**decimals

        print("Token", token.functions.symbol().call(), "has", decimals, "decimals, multiplier is", decimal_multiplier)

        print("Getting events")
        events = contract.events.Issued().createFilter(fromBlock=0).get_all_entries()

        print("Writing results to", csv_file)

        # Block number -> timestamp mappings
        timestamps = {}

        # Load cached timestamps
        if os.path.exists(timestamp_filename):
            with open(timestamp_filename, "rt") as inp:
                timestamps = json.load(inp)

        with open(csv_file, 'w', newline='') as out:
            writer = csv.writer(out)

            writer.writerow(["External id", "Payment at", "Tx hash", "Received tokens"])

            for idx, e in enumerate(events):

                if idx % 100 == 0:
                    print("Writing event", idx)
                    # Save cached timestamps
                    with open(timestamp_filename, "wt") as out:
                        json.dump(timestamps, out)

                block_number = e["blockNumber"]
                if block_number not in timestamps:
                    timestamps[block_number] = web3.eth.getBlock(block_number)["timestamp"]

                amount = Decimal(e["args"]["amount"])
                external_id = e["args"]["id"]

                tokens = amount / decimal_multiplier
                tokens = tokens.quantize(Decimal(10 ** -decimals))

                timestamp = timestamps[block_number]
                dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
                writer.writerow([
                    external_id,
                    dt.isoformat(),
                    e["transactionHash"],
                    str(tokens),
                ])

        print("Total", len(events), "issued events")
        print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
