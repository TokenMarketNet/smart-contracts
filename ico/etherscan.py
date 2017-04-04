"""etherscan.io utilities."""

import requests

from populus import Project

from ico.importexpand import expand_contract_imports


def verify_contract(project: Project, chain_name: str, address: str, contract_name, contract_filename: str, constructor_args: str, libraries: dict, optimization=True, compiler: str="v0.4.8-nightly.2017.1.13+commit.bde0b406"):
    """Make a contract verified on Etherscan.

    See the page in action: https://etherscan.io/verifyContract?a=0xcd111aa492a9c77a367c36e6d6af8e6f212e0c8e
    """

    src = expand_contract_imports(project, contract_filename)

    if chain_name == "mainnet":
        url = "https://etherscan.io/verifyContract"
    elif chain_name == "ropsten":
        url = "https://ropsten.etherscan.io/verifyContract"
    else:
        raise RuntimeError("Unknown chain")

    data = {
        "ctl00$ContentPlaceHolder1$txtContractAddress": address,
        "ctl00$ContentPlaceHolder1$txtContractName": contract_name,
        "ctl00$ContentPlaceHolder1$ddlCompilerVersions": compiler,
        "ctl00$ContentPlaceHolder1$ddlOptimization": "1" if optimization else "0",
        "ctl00$ContentPlaceHolder1$txtSourceCode": src,
        "ctl00$ContentPlaceHolder1$txtConstructorArguements": constructor_args,
    }

    idx = 1
    for library_name, library_address in libraries.items():
        data["ctl00$ContentPlaceHolder1$txtLibraryAddress{}".format(idx)] = library_address
        data["ctl00$ContentPlaceHolder1$txtLibraryName{}".format(idx)] = library_name

    resp = requests.post(url, data)
    resp.raise_for_status()

