"""Load a token vault."""
import csv
import time

import click
from decimal import Decimal

import sys
from eth_utils import from_wei, is_checksum_address, to_checksum_address
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


def load(chain, web3: Web3, address: str, csv_file: str, token: Contract, address_column: str, amount_column: str, duration_column: str, vault_address: str, override_checksum: bool):

    decimals = token.functions.decimals().call()
    decimal_multiplier = 10 ** decimals
    transaction = {"from": address}

    TokenVault = chain.provider.get_base_contract_factory('TokenVault')
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
        raise RuntimeError("Expected total amount {}, CSV sum is {}".format(token_vault.functions.tokensToBeAllocated().call(), int(total * decimal_multiplier)))

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

        duration = int(row[duration_column].strip())
        if duration > 0:
            tokens_per_second = int(tokens / duration)
        else:
            tokens_per_second = 0

        print("Row", i, "giving", tokens, "to", addr, "vault", token_vault.address, "time passed", time.time() - start_time, "ETH spent", spent)

        if not is_checksum_address(addr):
            if override_checksum:
                print("WARNING: not a checksummed Ethereum address at row", i, ":", format(addr))
                addr = to_checksum_address(addr)
            else:
                raise RuntimeError("Address not checksummed", addr, "Use --override-checksum to override if you know what you are doing.")

        if token_vault.functions.balances(addr).call() > 0:
            print("Already issued, skipping")
            continue

        txid = token_vault.functions.setInvestor(addr, tokens, tokens_per_second).transact(transaction)

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
    TokenVault = chain.provider.get_base_contract_factory('TokenVault')
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


def inspect(chain, vault_address: str, decimals: int):
    TokenVault = chain.provider.get_base_contract_factory('TokenVault')
    token_vault = TokenVault(address=vault_address)
    decimal_multiplier = 10 ** decimals
    claiming_starts = token_vault.functions.freezeEndsAt().call()
    csv_row = "{addr},{amount},{claimed},{curr},{tps},{tph},{tpd},{final}"
    csv_first_row = {
        "addr": "address",
        "amount": "amount",
        "claimed": "claimed",
        "curr": "currently claimable",
        "tps": "tokens per second",
        "tph": "tokens per hour",
        "tpd": "tokens per day",
        "final": "final claim after"
    }

    print (csv_row.format(**csv_first_row))

    events = token_vault.events.Allocated().createFilter(fromBlock=0).get_all_entries()

    for e in events:
        participant_addr = e["args"]["investor"]
        participant_balance = token_vault.functions.balances(participant_addr).call()
        participant_claimed = token_vault.functions.claimed(participant_addr).call()
        participant_tokens_per_second = token_vault.functions.tokensPerSecond(participant_addr).call()
        participant_currently_claimable = token_vault.functions.getCurrentlyClaimableAmount(participant_addr).call()

        final_claim = int(claiming_starts + (participant_balance / participant_tokens_per_second))
        hourly_tap = participant_tokens_per_second * 3600
        daily_tap = participant_tokens_per_second * 86400

        participant_row = {
            "addr": participant_addr,
            "amount": participant_balance / decimal_multiplier,
            "claimed": participant_claimed / decimal_multiplier,
            "curr": participant_currently_claimable / decimal_multiplier,
            "tps": participant_tokens_per_second / decimal_multiplier,
            "tph": hourly_tap / decimal_multiplier,
            "tpd": daily_tap / decimal_multiplier,
            "final": time.ctime(final_claim)
        }
        print(csv_row.format(**participant_row))

@click.command()
@click.option('--action', nargs=1, help='One of: deploy, load, lock', required=False, default=None)
@click.option('--chain', nargs=1, default="mainnet", help='On which chain to deploy - see populus.json')
@click.option('--address', nargs=1, help='The account that deploys the vault contract, controls the contract and pays for the gas fees', required=True)
@click.option('--token-address', nargs=1, help='Token contract address', required=True)
@click.option('--csv-file', nargs=1, help='CSV file containing distribution data', required=False)
@click.option('--address-column', nargs=1, help='Name of CSV column containing Ethereum addresses', default="address")
@click.option('--amount-column', nargs=1, help='Name of CSV column containing decimal token amounts', default="amount")
@click.option('--duration-column', nargs=1, help='Name of CSV column containing duration of vesting, in seconds if tap is enabled, 0 otherwise', default="duration")
@click.option('--limit', nargs=1, help='How many items to import in this batch', required=False, default=1000)
@click.option('--start-from', nargs=1, help='First row to import (zero based)', required=False, default=0)
@click.option('--vault-address', nargs=1, help='The address of the vault contract - leave out for the first run to deploy a new issuer contract', required=False, default=None)
@click.option('--freeze-ends-at', nargs=1, help='UNIX timestamp when vault freeze ends for deployment', required=False, default=None, type=int)
@click.option('--tokens-to-be-allocated', nargs=1, help='Manually verified count of tokens to be set in the vault', required=False, default=None, type=int)
@click.option('--override-checksum', is_flag=True, help='Skip checksum checks for addresses. Use this only if you understand the risks')
@click.option('--print-timestamp', is_flag=True, help='Print timestamp in the end of the output')
@click.option('--less-verbose', is_flag=True, help='Only print meaningful output. Ideal for CSV exports')
def main(chain, address, token_address, csv_file, limit, start_from, vault_address, address_column, amount_column, duration_column, action, freeze_ends_at, tokens_to_be_allocated, override_checksum, print_timestamp, less_verbose):
    """TokenVault control script.

    1) Deploys a token vault contract

    2) Reads in distribution data as CSV

    3) Locks vault
    """

    project = Project()

    with project.get_chain(chain) as c:

        web3 = c.web3

        # Goes through geth account unlock process if needed
        if is_account_locked(web3, address):
            request_account_unlock(c, address, timeout=3600*6)
            assert not is_account_locked(web3, address)

        Token = c.provider.get_base_contract_factory('FractionalERC20')
        token = Token(address=token_address)

        try:
            decimals = token.functions.decimals().call()
        except ValueError:
            sys.exit("Token contract does not have support for decimal places, cannot work with it")

        assert decimals >= 0

        if not less_verbose:
            print("Web3 provider is", web3.providers[0])
            print("Owner address is", address)
            print("Owner balance is", from_wei(web3.eth.getBalance(address), "ether"), "ETH")
            print("Total supply is", token.functions.totalSupply().call())
            print("Token decimal places is", decimals)

        if action == "deploy":
            deploy(project, c, chain, web3, address, token, freeze_ends_at, tokens_to_be_allocated * (10**decimals))
            print("TokenVault deployed.")
        elif action == "load":

            if vault_address == None:
                sys.exit("vault_address missing")

            if address_column == None:
                sys.exit("address_column missing")

            if amount_column == None:
                sys.exit("amount_column missing")

            load(c, web3, address, csv_file, token, address_column, amount_column, duration_column, vault_address, override_checksum)
            print("Data loaded to the vault.")
        elif action == "lock":
            lock(c, web3, address, token, vault_address)
            print("Vault locked. Now duck and wait.")
        elif action == "inspect":
            inspect(c, vault_address, decimals)
        else:
            sys.exit("Unknown action: {}".format(action))

        if print_timestamp:
            print(time.ctime(time.time()))


if __name__ == "__main__":
    main()
