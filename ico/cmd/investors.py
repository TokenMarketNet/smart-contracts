"""Extract crowdsale investor data."""
import csv
import datetime
from collections import OrderedDict

import click
from eth_utils import from_wei
from populus import Project


@click.command()
@click.option('--chain', nargs=1, default="mainnet", help='On which chain to deploy - see populus.json')
@click.option('--address', nargs=1, help='CrowdsaleContract address to scan', required=True)
@click.option('--csv-file', nargs=1, help='CSV fil to write', default=None)
def main(chain, address, csv_file):
    """Extract crowdsale contract investors."""

    project = Project()

    with project.get_chain(chain) as c:

        web3 = c.web3
        print("Web3 provider is", web3.providers[0])
        # Sanity check
        print("Block number is", web3.eth.blockNumber)

        Crowdsale = c.provider.get_contract_factory('MintedTokenCappedCrowdsale')
        crowdsale = Crowdsale(address=address)

        print("Total amount raised is", from_wei(crowdsale.functions.weiRaised().call(), "ether"), "ether")

        print("Getting events")
        events = crowdsale.events.Invested().createFilter(fromBlock=0).get_all_entries()

        # Merge several transactions from the same address to one
        print("Analysing", len(events), "raw events")
        address_data = OrderedDict()
        for e in events:
            address = e["args"]["investor"]
            data = address_data.get(address, {})

            # TODO: Not sure if we get events in block order
            timestamp = web3.eth.getBlock(e["blockNumber"])["timestamp"]
            current_first = data.get("first_payment", 99999999999999999)
            if timestamp < current_first:
                data["first_payment"] = timestamp

            data["raised"] = data.get("raised", 0) + from_wei(e["args"]["weiAmount"], "ether")
            data["tokens"] = data.get("tokens", 0) + e["args"]["tokenAmount"]
            address_data[address] = data

        if csv_file:
            print("Writing results to", csv_file)
            with open(csv_file, 'w', newline='') as out:
                writer = csv.writer(out)

                writer.writerow(["Address", "First payment at", "Invested ETH", "Received tokens"])

                for address, data in address_data.items():
                    timestamp = data["first_payment"]
                    dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
                    writer.writerow([
                        address,
                        dt.isoformat(),
                        str(data["raised"]),
                        str(data["tokens"])
                    ])
        else:
            for address, data in address_data.items():
                timestamp = data["first_payment"]
                dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
                print(
                    address,
                    dt.isoformat(),
                    str(data["raised"]),
                    str(data["tokens"])
                )

        print("Total", len(address_data), "investors")
        print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
