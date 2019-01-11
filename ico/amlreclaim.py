"""AML token reclaim scripting before the token release.

This code is separated from the main script to make it more testable.
"""

import csv
import logging
from collections import namedtuple
from typing import List, Optional, Tuple

from web3.contract import Contract

from ico.utils import validate_ethereum_address, check_succesful_tx
from ico.utils import check_multiple_succesful_txs


logger = logging.getLogger(__name__)

#: A parsed CSV input entry
Entry = namedtuple("Entry", ("address", "label"))


def reclaim_address(token: Contract, entry: Entry, tx_params: dict) -> Tuple[int, str]:
    """Reclsaim tokens for a single participant.

    :param token: Token contract we reclaim
    :param owner: Token owner account
    :param address: Etherereum address
    :param label: User notification label regarding this address
    :param tx_params: Ethereum transaction parameters to use
    :return: 1 on reclaim, 0 on skip
    """

    # Make sure we are not fed bad input, raises
    validate_ethereum_address(entry.address)

    if token.functions.balanceOf(entry.address).call() == 0:
        logger.info("%s: looks like already reclaimed %s", entry.address, entry.label)
        return 0, None

    txid = token.functions.transferToOwner(entry.address).transact(tx_params)
    logger.info("%s: reclaiming %s in txid %s", entry.address, entry.label, txid)
    return 1, txid


def reclaim_all(token: Contract, reclaim_list: List[Entry], tx_params: dict) -> int:
    """Reclaim all tokens from the given input sheet.

    Process transactions parallel to speed up the operation.

    :param tx_parms: Ethereum transaction parameters to use
    """

    total_reclaimed = 0

    tx_to_confirm = []  # List of txids to confirm
    tx_batch_size = 16  # How many transactions confirm once
    web3 = token.web3

    for entry in reclaim_list:
        ops, txid = reclaim_address(token, entry, tx_params)
        total_reclaimed += ops

        if not txid:
            # Already reclaimed
            continue

        tx_to_confirm.append(txid)

        # Confirm N transactions when batch max size is reached
        if len(tx_to_confirm) >= tx_batch_size:
            check_multiple_succesful_txs(web3, tx_to_confirm)
            tx_to_confirm = []

    # Confirm dangling transactions
    check_multiple_succesful_txs(web3, tx_to_confirm)

    return total_reclaimed


def prepare_csv(stream, address_key, label_key) -> List[Entry]:
    """Process CSV reclaim file.

    Make sure all Ethereum addresses are valid. Filter out duplicates.

    :param token: Token contract
    :param owner: ETH account set as the owner of the token
    :param stream: File stream for CSV
    :param address_key: Column holding ETH address in the CSV
    :param label_key: Column holding human readable description of the address in CSV
    :return: Number of total reclaims performed
    """

    reader = csv.DictReader(stream)
    rows = [row for row in reader]
    output_rows = []
    uniq = set()

    # Prevalidate addresses
    # Here we do it inline and make skip addresses that are not valid.
    for idx, row in enumerate(rows):
        addr = row[address_key].strip()
        label = row[label_key].strip()

        if not addr:
            # Empty cell / row
            continue

        if not addr.startswith("0x"):
            addr = "0x" + addr

        try:
            if addr:
                validate_ethereum_address(addr)
        except ValueError as e:
            logger.error("Invalid Ethereum address on row:%d address:%s label:%s reason:%s", idx+1, addr, label, str(e))
            continue

        if addr in uniq:
            logger.warn("Address has duplicates: %s", addr)
            continue

        uniq.add(addr)

        output_row = Entry(address=addr, label=label)
        output_rows.append(output_row)

    return output_rows


def count_tokens_to_reclaim(token, rows: List[Entry]):
    """Count how many tokens are on user balances to reclaim."""

    total = 0

    for idx, entry in enumerate(rows):
        total += token.functions.balanceOf(entry.address).call()

        if idx % 20 == 0:
            logger.info("Prechecking balances %d / %d", idx, len(rows))

    return total
