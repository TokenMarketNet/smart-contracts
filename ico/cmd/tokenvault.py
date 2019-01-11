"""Load a token vault."""
import csv
import time

import click
from decimal import Decimal

import sys
from eth_utils import from_wei
from web3 import Web3
from web3.contract import Contract

from populus.utils.accounts import is_account_locked
from populus import Project
from populus.utils.cli import request_account_unlock

from ico.utils import check_succesful_tx
from ico.utils import check_multiple_succesful_txs
from ico.etherscan import verify_contract
from ico.etherscan import get_etherscan_link
from ico.utils import get_constructor_arguments


def deploy(project: Project, chain, chain_name, web3: Web3, address: str, token: Contract, freeze_ends_at: int, tokens_to_be_allocated: int):

    # TODO: Fix Populus support this via an deploy argument
    if "JSONFile" in chain.registrar.registrar_backends:
        del chain.registrar.registrar_backends["JSONFile"]

    freeze_ends_at = int(freeze_ends_at)
    assert freeze_ends_at > 0
    assert tokens_to_be_allocated > 0

    # Create issuer contract
    args = [
        address,
        freeze_ends_at,
        token.address,
        tokens_to_be_allocated,
    ]

    transaction = {
        "from": address,
    }

    print("Deploying new TokenVault contract", args)
    token_vault, txhash = chain.provider.deploy_contract("TokenVault", deploy_transaction=transaction, deploy_args=args)
    check_succesful_tx(web3, txhash)

    const_args = get_constructor_arguments(token_vault, args)
    fname = "TokenVault.sol"
    browser_driver = "chrome"
    verify_contract(
        project=project,
        libraries={},
        chain_name=chain_name,
        address=token_vault.address,
        contract_name="TokenVault",
        contract_filename=fname,
        constructor_args=const_args,
        browser_driver=browser_driver)
    link = get_etherscan_link(chain_name, token_vault.address)

    print("TokenVault verified contract is", link)
    return token_vault


def load(chain, web3: Web3, address: str, csv_file: str, token: Contract, address_column: str, amount_column: str, vault_address: str):

    decimals = token.functions.decimals().call()
    decimal_multiplier = 10 ** decimals
    transaction = {"from": address}

    TokenVault = chain.contract_factories.TokenVault
    token_vault = TokenVault(address=vault_address)

    # Check that our tokens are the same
    assert token_vault.functions.token().call() == token.address

    print("Starting to import investor data to ", token_vault.address)

    print("Reading data", csv_file)
    with open(csv_file, "rt") as inp:
        reader = csv.DictReader(inp)
        rows = [row for row in reader]

    # Check that we have unique addresses
    uniq_addresses = set()
    total = 0
    for row in rows:
        addr = row[address_column].strip()
        amount = row[amount_column].strip()
        if addr in uniq_addresses:
            raise RuntimeError("Address appears twice in input data", addr)
        uniq_addresses.add(addr)
        amount = Decimal(amount)
        total += amount
        if amount <= 0:
            raise RuntimeError("Invalid amount:".format(amount))

    if token_vault.functions.tokensToBeAllocated().call() != total * decimal_multiplier:
        raise RuntimeError("Expected total amount {}, CSV sum is {}".format(token_vault.functions.tokensToBeAllocated().call(), total))

    # Start distribution
    start_time = time.time()
    start_balance = from_wei(web3.eth.getBalance(address), "ether")

    tx_to_confirm = []  # List of txids to confirm
    tx_batch_size = 16  # How many transactions confirm once

    print("Total rows", len(rows))

    for i in range(len(rows)):
        data = rows[i]
        addr = data[address_column].strip()
        tokens = Decimal(data[amount_column].strip())

        tokens *= decimal_multiplier

        end_balance = from_wei(web3.eth.getBalance(address), "ether")
        spent = start_balance - end_balance

        # http://stackoverflow.com/a/19965088/315168
        if not tokens % 1 == 0:
            raise RuntimeError("Could not issue tokens because after multiplication was not integer")

        tokens = int(tokens)

        print("Row", i, "giving", tokens, "to", addr, "vault", token_vault.address, "time passed", time.time() - start_time, "ETH spent", spent)

        if token_vault.functions.balances(addr).call() > 0:
            print("Already issued, skipping")
            continue

        txid = token_vault.functions.setInvestor(addr, tokens).transact(transaction)

        tx_to_confirm.append(txid)

        # Confirm N transactions when batch max size is reached
        if len(tx_to_confirm) >= tx_batch_size:
            check_multiple_succesful_txs(web3, tx_to_confirm)
            tx_to_confirm = []

    # Confirm dangling transactions
    check_multiple_succesful_txs(web3, tx_to_confirm)

    end_balance = from_wei(web3.eth.getBalance(address), "ether")
    print("Deployment cost is", start_balance - end_balance, "ETH")


def lock(chain, web3: Web3, address: str, token: Contract, vault_address: str):
    TokenVault = chain.contract_factories.TokenVault
    token_vault = TokenVault(address=vault_address)

    print("Locking vault ", token_vault.address)
    print("Tokens expected", token_vault.functions.tokensToBeAllocated().call())
    print("Tokens allocated", token_vault.functions.tokensAllocatedTotal().call())
    print("Tokens hold", token_vault.functions.getBalance().call())

    if not(token_vault.functions.tokensToBeAllocated().call() == token_vault.functions.tokensAllocatedTotal().call() == token_vault.functions.getBalance().call()):
        sys.exit("Vault token balances mismatch")

    transaction = {
        "from": address,
    }

    print("Locking vault")
    txid = token_vault.transact(transaction).lock()
    check_succesful_tx(web3, txid)


@click.command()
@click.option('--action', nargs=1, help='One of: deploy, load, lock', required=False, default=None)
@click.option('--chain', nargs=1, default="mainnet", help='On which chain to deploy - see populus.json')
@click.option('--address', nargs=1, help='The account that deploys the vault contract, controls the contract and pays for the gas fees', required=True)
@click.option('--token-address', nargs=1, help='Token contract address', required=True)
@click.option('--csv-file', nargs=1, help='CSV file containing distribution data', required=False)
@click.option('--address-column', nargs=1, help='Name of CSV column containing Ethereum addresses', default="address")
@click.option('--amount-column', nargs=1, help='Name of CSV column containing decimal token amounts', default="amount")
@click.option('--limit', nargs=1, help='How many items to import in this batch', required=False, default=1000)
@click.option('--start-from', nargs=1, help='First row to import (zero based)', required=False, default=0)
@click.option('--vault-address', nargs=1, help='The address of the vault contract - leave out for the first run to deploy a new issuer contract', required=False, default=None)
@click.option('--freeze-ends-at', nargs=1, help='UNIX timestamp when vault freeze ends for deployment', required=False, default=None, type=int)
@click.option('--tokens-to-be-allocated', nargs=1, help='Manually verified count of tokens to be set in the vault', required=False, default=None, type=int)
def main(chain, address, token_address, csv_file, limit, start_from, vault_address, address_column, amount_column, action, freeze_ends_at, tokens_to_be_allocated):
    """TokenVault control script.

    1) Deploys a token vault contract

    2) Reads in distribution data as CSV

    3) Locks vault
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

        Token = c.contract_factories.FractionalERC20
        token = Token(address=token_address)

        print("Total supply is", token.functions.totalSupply().call())

        try:
            decimals = token.functions.decimals().call()
        except ValueError:
            sys.exit("Token contract does not have support for decimal places, cannot work with it")

        print("Token decimal places is", decimals)
        assert decimals >= 0

        if action == "deploy":
            deploy(project, c, chain, web3, address, token, freeze_ends_at, tokens_to_be_allocated * (10**decimals))
            print("TokenVault deployed.")
            sys.exit(0)
        elif action == "load":

            if vault_address == None:
                sys.exit("vault_address missing")

            if address_column == None:
                sys.exit("address_column missing")

            if amount_column == None:
                sys.exit("amount_column missing")

            load(c, web3, address, csv_file, token, address_column, amount_column, vault_address)
            print("Data loaded to the vault.")
            sys.exit(0)
        elif action == "lock":
            lock(c, web3, address, token, vault_address)
            print("Vault locked. Now duck and wait.")
        else:
            sys.exit("Unknown action: {}".format(action))


if __name__ == "__main__":
    main()
