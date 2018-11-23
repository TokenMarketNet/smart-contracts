"""Extract crowdsale raw investmetn data."""
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
    """Extract crowdsale invested events.

    This is useful for RelaunchCrowdsale to rebuild the data.
    """

    project = Project()
    timestamp_filename = "block-timestamps.json"

    with project.get_chain(chain) as c:

        web3 = c.web3
        print("Web3 provider is", web3.currentProvider)
        # Sanity check
        print("Block number is", web3.eth.blockNumber)

        Crowdsale = c.provider.get_base_contract_factory('MintedTokenCappedCrowdsale')
        crowdsale = Crowdsale(address=address)

        Token = c.provider.get_base_contract_factory('CrowdsaleToken')
        token = Token(address=crowdsale.functions.token().call())

        decimals = token.functions.decimals().call()
        decimal_multiplier = 10**decimals

        print("We have", decimals, "decimals, multiplier is", decimal_multiplier)

        print("Total amount raised is", from_wei(crowdsale.functions.weiRaised().call(), "ether"), "ether")

        print("Getting events")
        events = crowdsale.events.Invested().createFilter(fromBlock=0).get_all_entries()

        print("Writing results to", csv_file)

        # Block number -> timestamp mappings
        timestamps = {}

        # Load cached timestamps
        if os.path.exists(timestamp_filename):
            with open(timestamp_filename, "rt") as inp:
                timestamps = json.load(inp)

        with open(csv_file, 'w', newline='') as out:
            writer = csv.writer(out)

            writer.writerow(["Address", "Payment at", "Tx hash", "Tx index", "Invested ETH", "Received tokens"])

            for idx, e in enumerate(events):

                if idx % 100 == 0:
                    print("Writing event", idx)
                    # Save cached timestamps
                    with open(timestamp_filename, "wt") as out:
                        json.dump(timestamps, out)

                block_number = e["blockNumber"]
                if block_number not in timestamps:
                    timestamps[block_number] = web3.eth.getBlock(block_number)["timestamp"]

                amount = Decimal(e["args"]["tokenAmount"]) / Decimal(decimal_multiplier)

                tokens = amount * decimal_multiplier

                # http://stackoverflow.com/a/19965088/315168
                if not tokens % 1 == 0:
                    raise RuntimeError("Could not convert token amount to decimal format. It was not an integer after restoring non-fractional balance: {} {} {}".format(tokens, amount, decimal_multiplier))

                timestamp = timestamps[block_number]
                dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
                writer.writerow([
                    e["args"]["investor"],
                    dt.isoformat(),
                    e["transactionHash"],
                    e["transactionIndex"],
                    from_wei(e["args"]["weiAmount"], "ether"),
                    amount,
                ])

        print("Total", len(events), "invest events")
        print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
