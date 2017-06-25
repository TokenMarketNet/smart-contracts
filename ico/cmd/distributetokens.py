"""Distribute tokens in centrally issued crowdsale."""
import csv
import time

import click
from decimal import Decimal

import sys
from eth_utils import from_wei
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
@click.option('--limit', nargs=1, help='How many items to import in this batch', required=False, default=1000)
@click.option('--start-from', nargs=1, help='First row to import (zero based)', required=False, default=0)
@click.option('--issuer-address', nargs=1, help='The address of the issuer contract - leave out for the first run to deploy a new issuer contract', required=False, default=None)
@click.option('--master-address', nargs=1, help='The team multisig wallet address that does StandardToken.approve() for the issuer contract', required=False, default=None)
@click.option('--allow-zero/--no-allow-zero', default=False, help='Stops the script if a zero amount row is encountered')
def main(chain, address, token, csv_file, limit, start_from, issuer_address, address_column, amount_column, allow_zero, master_address):
    """Distribute tokens to centrally issued crowdsale participant.

    Reads in distribution data as CSV. Then uses Issuer contract to distribute tokens.
    All token counts are multiplied by token contract decimal specifier. E.g. if CSV has amount 15.5,
    token has 2 decimal places, we will issue out 1550 raw token amount.

    To speed up the issuance, transactions are verified in batches. Each batch is 16 transactions at a time.

    Example (first run):

        distribute-tokens --chain=kovan --address=0x001FC7d7E506866aEAB82C11dA515E9DD6D02c25 --token=0x1644a421ae0a0869bac127fa4cce8513bd666705 --csv-file=input.csv --allow-zero --address-column="Ethereum address" --amount-column="Golden tickets earned"

    Example (second run, continue after first run was interrupted):

        distribute-tokens --chain=kovan --address=0x001FC7d7E506866aEAB82C11dA515E9DD6D02c25 --token=0x1644a421ae0a0869bac127fa4cce8513bd666705 --csv-file=input.csv --allow-zero --address-column="Ethereum address" --amount-column="Golden tickets earned" --issuer-address=0x2c9877534f62c8b40aebcd08ec9f54d20cb0a945

    """

    project = Project()

    with project.get_chain(chain) as c:

        web3 = c.web3
        print("Web3 provider is", web3.currentProvider)
        print("Owner address is", address)
        print("Owner balance is", from_wei(web3.eth.getBalance(address), "ether"), "ETH")

        # Goes through geth account unlock process if needed
        if is_account_locked(web3, address):
            request_account_unlock(c, address, timeout=3600*6)
            assert not is_account_locked(web3, address)

        Token = c.provider.get_base_contract_factory('CentrallyIssuedToken')
        token = Token(address=token)

        print("Token is", token.address)
        print("Total supply is", token.call().totalSupply())
        print("Upgrade master is", token.call().upgradeMaster())
        print("Owner token balance master is", token.call().balanceOf(address))

        decimals = token.call().decimals()
        print("Token decimal places is", decimals)
        assert decimals >= 0

        decimal_multiplier = 10**decimals

        transaction = {"from": address}

        Issuer = c.provider.get_base_contract_factory('Issuer')
        if not issuer_address:

            # TODO: Fix Populus support this via an deploy argument
            if "JSONFile" in c.registrar.registrar_backends:
                del c.registrar.registrar_backends["JSONFile"]

            # Create issuer contract
            assert master_address, "You need to give master-address"
            args = [address, master_address, token.address]
            print("Deploying new issuer contract", args)
            issuer, txhash = c.provider.deploy_contract("Issuer", deploy_transaction=transaction, deploy_args=args)
            check_succesful_tx(web3, txhash)

            const_args = get_constructor_arguments(issuer, args)
            chain_name = chain
            fname = "Issuer.sol"
            browser_driver = "chrome"
            verify_contract(
                project=project,
                libraries={},  # TODO: Figure out how to pass around
                chain_name=chain_name,
                address=issuer.address,
                contract_name="Issuer",
                contract_filename=fname,
                constructor_args=const_args,
                # libraries=runtime_data["contracts"][name]["libraries"],
                browser_driver=browser_driver)
            link = get_etherscan_link(chain_name, issuer.address)

            print("Issuer verified contract is", link)
        else:
            print("Reusing existing issuer contract")
            issuer = Issuer(address=issuer_address)

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

        # Check that we have unique addresses
        uniq_addresses = set()
        for row in rows:
            addr = row[address_column].strip()
            if addr in uniq_addresses:
                raise RuntimeError("Address appears twice in input data", addr)
            uniq_addresses.add(addr)

        # Start distribution
        start_time = time.time()
        start_balance = from_wei(web3.eth.getBalance(address), "ether")

        tx_to_confirm = []   # List of txids to confirm
        tx_batch_size = 16  # How many transactions confirm once

        print("Total rows", len(rows))

        for i in range(start_from, min(start_from+limit, len(rows))):
            data = rows[i]
            addr = data[address_column].strip()
            tokens = Decimal(data[amount_column].strip())

            tokens *= decimal_multiplier

            end_balance = from_wei(web3.eth.getBalance(address), "ether")
            spent = start_balance - end_balance

            if tokens == 0:
                if not allow_zero:
                    raise RuntimeError("Encountered zero amount")
                else:
                    continue

            # http://stackoverflow.com/a/19965088/315168
            if not tokens % 1 == 0:
                raise RuntimeError("Could not issue tokens because after multiplication was not integer")

            tokens = int(tokens)

            print("Row", i,  "giving", tokens, "to", addr, "issuer", issuer.address, "time passed", time.time() - start_time, "ETH passed", spent)

            if issuer.call().issued(addr):
                print("Already issued, skipping")
                continue

            txid = issuer.transact(transaction).issue(addr, tokens)

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
