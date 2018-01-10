"""Distribute tokens in centrally issued crowdsale using an external id."""
import csv
import time

import click
from decimal import Decimal

import sys
from eth_utils import from_wei, to_wei
from populus.utils.accounts import is_account_locked
from populus import Project
from populus.utils.cli import request_account_unlock

from ico.utils import check_succesful_tx
from ico.utils import check_multiple_succesful_txs
from ico.etherscan import verify_contract
from ico.etherscan import get_etherscan_link
from ico.utils import get_constructor_arguments


@click.command()
@click.option('--chain', nargs=1, default="mainnet", help='On which chain to deploy - see populus.json')
@click.option('--address', nargs=1, help='The account that deploys the issuer contract, controls the contract and pays for the gas fees', required=True)
@click.option('--token', nargs=1, help='Token contract address', required=True)
@click.option('--csv-file', nargs=1, help='CSV file containing distribution data', required=True)
@click.option('--address-column', nargs=1, help='Name of CSV column containing Ethereum addresses', default="address")
@click.option('--amount-column', nargs=1, help='Name of CSV column containing decimal token amounts', default="amount")
@click.option('--external-id-column', nargs=1, help='Name of CSV column containing the external id', default="external_id")
@click.option('--limit', nargs=1, help='How many items to import in this batch', required=False, default=1000)
@click.option('--start-from', nargs=1, help='First row to import (zero based)', required=False, default=0)
@click.option('--issuer-address', nargs=1, help='The address of the issuer contract - leave out for the first run to deploy a new issuer contract', required=False, default=None)
@click.option('--gas-price', nargs=1, help='Override gas price. If not set use the default * 2.0. Specify in Gwei e.g. 50.', required=False, default=None)
@click.option('--master-address', nargs=1, help='The team multisig wallet address that does StandardToken.approve() for the issuer contract', required=False, default=None)
@click.option('--solc-version', nargs=1, help='Menu item for the solc compiler verification on EtherScan', required=False, default="v0.4.16+commit.d7661dd9")
@click.option('--allow-addresless', default=True, help='If address column is not filled in skip the participant')
def main(chain, address, token, csv_file, limit, start_from, issuer_address, address_column, amount_column, external_id_column, allow_addresless, master_address, gas_price, solc_version):
    """Distribute tokens to centrally issued crowdsale participant or bounty program participants using an external key.

    Reads in distribution data as CSV. Then uses Issuer contract to distribute tokens.
    All token counts are multiplied by token contract decimal specifier. E.g. if CSV has amount 15.5,
    token has 2 decimal places, we will issue out 1550 raw token amount.

    The external id uniquely identifies participants. This is different from the distribute-tokens where the
    Ethereum address uniquely identifies participants.

    To speed up the issuance, transactions are verified in batches. Each batch is 16 transactions at a time.

    First have a issuer contract created:

        distribute-tokens-ext-id \
          --chain=mainnet \
          --address=0xccba4928c4e9d10242788d9cf144d865348c6c7f \
          --token=0x1a7a8bd9106f2b8d977e08582dc7d24c723ab0db \
          --master-address=0xa684a3371e0d46bca4a6db1ff538a44f1440a855 \
          --csv-file=data.csv \
          --address-column="Ethereum address" \
          --amount-column="Token amount" \
          --external-id-column="External ID number" \
          --solc-version="v0.4.16+commit.d7661dd9" \
          --gas-price=100

    Then perform EIP-20 approve() to give tokens to the issuer contract deployed in the last command.

    Then run the distribution:

        distribute-tokens-ext-id \
          --chain=mainnet \
          --address=0xccba4928c4e9d10242788d9cf144d865348c6c7f \
          --token=0x1a7a8bd9106f2b8d977e08582dc7d24c723ab0db \
          --master-address=0xa684a3371e0d46bca4a6db1ff538a44f1440a855 \
          --issuer-address=0x60cfb02266310e66dd99b1635e702c519a564726 \
          --csv-file=combined.csv \
          --address-column="Address" \
          --amount-column="Amount" \
          --gas-price=70 \
          --start-from=670
    """

    project = Project()

    with project.get_chain(chain) as c:

        web3 = c.web3
        print("Web3 provider is", web3.currentProvider)
        print("Deployer account address is", address)
        print("Deployer account balance is", from_wei(web3.eth.getBalance(address), "ether"), "ETH")

        # Goes through geth account unlock process if needed
        if is_account_locked(web3, address):
            request_account_unlock(c, address, timeout=3600*6)
            assert not is_account_locked(web3, address)

        Token = c.provider.get_base_contract_factory('CentrallyIssuedToken')
        token = Token(address=token)

        print("Token is", token.address)
        print("Total supply is", token.call().totalSupply())
        print("Upgrade master is", token.call().upgradeMaster())
        print("Deployer account token balance is", token.call().balanceOf(address))

        decimals = token.call().decimals()
        print("Token decimal places is", decimals)
        assert decimals >= 0

        decimal_multiplier = 10**decimals

        if gas_price:
            gas_price = int(gas_price) * 10**9
        else:
            gas_price = web3.eth.gasPrice * 2

        transaction = {
            "from": address,
            "gasPrice": gas_price
        }

        print("Using gas price of", gas_price / 10**9, "GWei")

        IssuerWithId = c.provider.get_base_contract_factory('IssuerWithId')
        if not issuer_address:

            # TODO: Fix Populus support this via an deploy argument
            if "JSONFile" in c.registrar.registrar_backends:
                del c.registrar.registrar_backends["JSONFile"]

            # Create issuer contract
            assert master_address, "You need to give master-address"
            args = [address, master_address, token.address]
            print("Deploying new issuer contract", args, "transaction parameters", transaction)
            issuer, txhash = c.provider.deploy_contract("IssuerWithId", deploy_transaction=transaction, deploy_args=args)

            print("Deployment transaction is", txhash)
            print("Waiting contract to be deployed")
            check_succesful_tx(web3, txhash)

            const_args = get_constructor_arguments(issuer, args)
            print("Contract constructor arguments are", const_args)
            chain_name = chain
            fname = "IssuerWithId.sol"
            browser_driver = "chrome"
            verify_contract(
                project=project,
                libraries={},  # TODO: Figure out how to pass around
                chain_name=chain_name,
                address=issuer.address,
                contract_name="IssuerWithId",
                contract_filename=fname,
                constructor_args=const_args,
                browser_driver=browser_driver,
                compiler=solc_version)
            link = get_etherscan_link(chain_name, issuer.address)
            print("Issuer verified contract is", link)
        else:
            print("Using existing issuer contract")
            issuer = IssuerWithId(address=issuer_address)

        print("Issuer contract is", issuer.address)
        print("Currently issued", issuer.call().issuedCount())

        if not master_address:
            sys.exit("Please use Token.approve() to give some allowance for the issuer contract by master address")

        allowance = token.call().allowance(master_address, issuer.address)
        print("Issuer allowance", allowance)

        if allowance == 0 or not master_address:
            sys.exit("Please use Token.approve() to give some allowance for the issuer contract by master address")

        print("Reading data", csv_file)
        with open(csv_file, "rt") as inp:
            reader = csv.DictReader(inp)
            rows = [row for row in reader]

        # Start distribution
        start_time = time.time()
        start_balance = from_wei(web3.eth.getBalance(address), "ether")

        tx_to_confirm = []   # List of txids to confirm
        tx_batch_size = 16  # How many transactions confirm once

        print("Total rows", len(rows))

        for i in range(start_from, min(start_from+limit, len(rows))):
            data = rows[i]
            addr = data[address_column].strip()
            external_id = data[external_id_column].strip()
            tokens = Decimal(data[amount_column].strip())

            tokens *= decimal_multiplier

            end_balance = from_wei(web3.eth.getBalance(address), "ether")
            spent = start_balance - end_balance

            if addr == "":
                if not allow_addresless:
                    raise RuntimeError("Encountered missing address")
                else:
                    continue

            if not external_id:
                raise RuntimeError("Missing external id on row #{}".format(i+1))

            # http://stackoverflow.com/a/19965088/315168
            if not tokens % 1 == 0:
                raise RuntimeError("Could not issue tokens because after multiplication was not integer")

            transaction = {
                "from": address,
                "gasPrice": gas_price,
                "gas": 100000,  # Use 100k gas unit limit
            }

            tokens = int(tokens)
            external_id = int(external_id)

            if not external_id > 0:
                raise RuntimeError("External id must be a positive integer on row #{}".format(i+1))

            print("Row", i,  "giving", tokens, "to", addr, "issuer", issuer.address, "time passed", time.time() - start_time, "ETH passed", spent, "gas price", transaction["gasPrice"] / (10**9))

            if issuer.call().issued(external_id):
                print("Already issued, skipping")
                continue

            txid = issuer.transact(transaction).issue(addr, tokens, external_id)
            tx_to_confirm.append(txid)

            # Confirm N transactions when batch max size is reached
            if len(tx_to_confirm) >= tx_batch_size:
                check_multiple_succesful_txs(web3, tx_to_confirm)
                tx_to_confirm = []

        # Confirm dangling transactions
        check_multiple_succesful_txs(web3, tx_to_confirm)

        end_balance = from_wei(web3.eth.getBalance(address), "ether")
        print("Deployment cost is", start_balance - end_balance, "ETH")
        print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
