"""Deploy crowdsale and all related contracts contract."""

import click
from populus import Project

from ico.deploy import deploy_crowdsale_from_file


@click.command()
@click.option('--deployment-name', nargs=1, default="mainnet", help='Project section id inside the YAML file. The topmost YAML key. Example YAML files use "mainnet" or "kovan".', required=True)
@click.option('--deployment-file', nargs=1, help='Deployment script YAML .yml file to process', required=True)
@click.option('--address', nargs=1, help='Your Ethereum account that is the owner of deployment and pays the gas cost. This account must exist on Ethereum node we connect to. Connection parameteres, port and IP, are defined in populus.json.', required=True)
def main(deployment_file, deployment_name, address):
    """Makes a scripted multiple contracts deployed based on a YAML file.

    Reads the chain configuration information from populus.json.
    The resulting deployed contracts can be automatically verified on etherscan.io.

    Example files:

    * https://github.com/TokenMarketNet/ico/blob/master/crowdsales/crowdsale-token-example.yml

    * https://github.com/TokenMarketNet/ico/blob/master/crowdsales/allocated-token-sale-example.yml

    * https://github.com/TokenMarketNet/ico/blob/master/crowdsales/example.yml
    """

    project = Project()
    deploy_crowdsale_from_file(project, deployment_file, deployment_name, address)
    print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
