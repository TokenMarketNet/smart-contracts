"""Extract crowdsale raw investmetn data."""
import csv
import datetime

import click
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

    with project.get_chain(chain) as c:

        web3 = c.web3
        print("Web3 provider is", web3.currentProvider)
        # Sanity check
        print("Block number is", web3.eth.blockNumber)

        Crowdsale = c.provider.get_contract_factory('MintedTokenCappedCrowdsale')
        crowdsale = Crowdsale(address=address)

        print("Total amount raised is", from_wei(crowdsale.call().weiRaised(), "ether"), "ether")

        print("Getting events")
        events = crowdsale.pastEvents("Invested").get(only_changes=False)

        print("Writing results to", csv_file)
        with open(csv_file, 'w', newline='') as out:
            writer = csv.writer(out)

            writer.writerow(["Address", "Payment at", "Tx hash", "Tx index", "Invested ETH", "Received tokens"])

            for e in events:
                timestamp = web3.eth.getBlock(e["blockNumber"])["timestamp"]
                dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
                writer.writerow([
                    address,
                    dt.isoformat(),
                    e["transactionHash"],
                    e["transactionIndex"],
                    from_wei(e["args"]["weiAmount"], "ether"),
                    e["args"]["tokenAmount"],
                ])

        print("Total", len(events), "invest events")
        print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
