"""Deploy crowdsale and all related contracts contract."""

import click
from populus import Project

from ico.deploy import deploy_crowdsale_from_file


@click.command()
@click.option('--deployment-name', nargs=1, default="mainnet", help='YAML section name we are deploying. Usual options include "mainnet" or "kovan"', required=True)
@click.option('--deployment-file', nargs=1, help='YAML file definiting the crowdsale', required=True)
@click.option('--address', nargs=1, help='Deployment address that pays the gas for the deployment cost. This account must exist on Ethereum node you are connected to.', required=True)
def main(deployment_file, deployment_name, address):
    """Makes a scripted multiple contracts deployed based on a YAML file.

    Reads the chain configuration information from populus.json.
    The resulting deployed contracts can be automatically verified on etherscan.io.

    Example:

        deploy-contracts --deployment-file=crowdsales/example.yml --deployment-name=kovan--address=0x001fc7d7e506866aeab82c11da515e9dd6d02c25

    Example files:

    * https://github.com/TokenMarketNet/ico/blob/master/crowdsales/allocated-token-sale-example.yml

    * https://github.com/TokenMarketNet/ico/blob/master/crowdsales/example.yml
    """

    project = Project()
    deploy_crowdsale_from_file(project, deployment_file, deployment_name, address)
    print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
