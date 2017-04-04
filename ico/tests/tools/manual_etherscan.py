from ico.etherscan import verify_contract
from populus import Project


def manual_etherscan():
    """Manual test verification on EtherScan.io."""

    contract_name = "PresaleFundCollector"
    address = "0xb589ef3af084cc5ec905d23112520ec168478582"
    constructor_args = "000000000000000000000000e8baf9df0ded92c5f28aab97f13936e7716a4a5b00000000000000000000000000000000000000000000000000000000590ba32f000000000000000000000000000000000000000000000002b5e3af16b1880000"
    libraries = {'SafeMathLib': '0x8fd011ad5d39da2f0a09c2d89e7d6ae861fe42ba'}

    p = Project()
    chain_name = "mainnet"

    verify_contract(
        project=p,
        chain_name=chain_name,
        address=address,
        contract_name="PresaleFundCollector",
        contract_filename="PresaleFundCollector.sol",
        constructor_args=constructor_args,
        libraries=libraries)


if __name__ == "__main__":
    manual_etherscan()
