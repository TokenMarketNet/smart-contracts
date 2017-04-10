"""Deploy crowdsale and all related contracts contract."""

import click
from populus import Project

from ico.deploy import deploy_crowdsale_from_file


@click.command()
@click.option('--deployment-name', nargs=1, default="mainnet", help='Which crowdsale definition section to deploy', required=True)
@click.option('--crowdsale-file', nargs=1, help='Yaml file definiting the crowdsale', required=True)
@click.option('--address', nargs=1, help='Address to deploy from and who becomes as a owner. This account must exist on Go-Ethereum we are connected to.', required=True)
def main(crowdsale_file, deployment_name, address):
    """Deploy a CrowdsaleToken contract.

    Example:

    deploy-crowdsale --crowdsale-file=crowdsales/example.yml --deployment-name=ropsten --address=0xffffffffffff
    """

    project = Project()
    deploy_crowdsale_from_file(project, crowdsale_file, deployment_name, address)
    print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
