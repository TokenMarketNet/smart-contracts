"""Combine multiple CSV files to a single token distribution."""

import csv
import collections
from decimal import Decimal, ROUND_HALF_DOWN
from typing import List

import click
import decimal
from eth_utils import is_address
from eth_utils import is_checksum_address
from eth_utils import to_checksum_address
from eth_utils import is_hex_address


class AddressEntry:
    """Keep track of a balance of a single address."""

    def __init__(self, amount: Decimal, sources: set, address_forms: set, count: int, rounded_amount: Decimal):
        self.amount = amount
        self.sources = sources
        self.count = count
        self.rounded_amount = rounded_amount
        self.address_forms = address_forms


def read_file(combined: dict, all_errors: List[tuple], book_keeping: collections.Counter, csv_file: str, decimals: int, address_column: str, amount_column: str):
    """Process a single CSV file."""

    rounder = Decimal(10) ** (-1 * decimals)

    sum = rounded_sum = Decimal(0)

    errors = []

    print("Reading file:", csv_file, "with rounder", rounder)
    with open(csv_file, "rt", encoding="utf-8", errors='ignore') as inp:
        reader = csv.DictReader(inp)
        rows = [row for row in reader]

        # First check all rows
        good_rows = []  # type: List[dict]
        for line, row in enumerate(rows, start=1):
            address = row[address_column]
            amount = row[amount_column]

            address = address.strip()
            amount = amount.strip()

            # Check for any Ethereum address
            if len(address) < 42:
                errors.append((csv_file, line, "Not an Ethereum address: {}".format(address)))
                continue

            try:
                if not is_hex_address(address):
                    errors.append((csv_file, line, "Not an Ethereum address: {}".format(address)))
                    continue
            except UnicodeEncodeError:
                errors.append([csv_file, line, "Could not decode: {}".format(address)])
                continue

            # Check if checksummed address if any of the letters is upper case
            if any([c.isupper() for c in address]):
                if not is_checksum_address(address):
                    errors.append((csv_file, line, "Not a checksummed Ethereum address: {}".format(address)))
                    continue

            try:
                amount = Decimal(amount)
            except (ValueError, decimal.InvalidOperation):
                errors.append((csv_file, line, "Bad decimal amount: {}".format(amount)))
                continue

            good_rows.append(row)

        # Then do a full pass on rows where users did not crap their data
        for row in good_rows:
            address = row[address_column].strip()
            amount = row[amount_column].strip()

            amount = Decimal(amount)
            rounded_amount = amount.quantize(rounder, rounding=ROUND_HALF_DOWN)  # Use explicit rounding

            sum += amount
            rounded_sum += rounded_amount

            # Make sure we use the same format for the addresses everywehre
            address = address.lower()

            entry = combined.get(address)
            if not entry:
                entry = AddressEntry(amount=Decimal(0), rounded_amount=Decimal(0), sources=set(), address_forms=set(), count=0)
                combined[address] = entry
                book_keeping["uniq_entries"] += 1

            entry.sources.add(csv_file)
            entry.address_forms.add(row[address_column])  # Record original spelling of the address
            entry.amount += amount
            entry.rounded_amount += rounded_amount

            book_keeping["token_total"] += rounded_amount

            entry.count += 1
            book_keeping["total_entries"] += 1

    all_errors += errors

    print("File:", csv_file, "total sum", sum)
    print("File:", csv_file, "rounded sum", rounded_sum)
    print("File:", csv_file, "errors", len(errors))


@click.command()
@click.option('--input-file', nargs=1, help='CSV file to read and combine. It should be given multiple times for different files.', default=None, required=True, multiple=True)
@click.option('--output-file', nargs=1, help='A CSV file to write the output', default=None, required=True)
@click.option('--decimals', nargs=1, help='A number of decimal points to use', default=None, required=True, type=int)
@click.option('--address-column', nargs=1, help='Name of CSV column containing Ethereum addresses', default="address")
@click.option('--amount-column', nargs=1, help='Name of CSV column containing decimal token amounts', default="amount")
def main(input_file: list, output_file: str, decimals: int, address_column: str, amount_column: str):
    """Combine multiple token distribution CSV files to a single CSV file good for an Issuer contract.

    - Input is a CSV file having columns Ethereum address, number of tokens

    - Round all tokens to the same decimal precision

    - Combine multiple transactions to a single address to one transaction

    Example of cleaning up one file:

        combine-csvs --input-file=csvs/bounties-unclean.csv --output-file=combine.csv --decimals=8 --address-column="address" --amount-column="amount"

    Another example - combine all CSV files in a folder using zsh shell:

        combine-csvs csvs/*.csv(P:--input-file:) --output-file=combined.csv --decimals=8 --address-column="Ethereum address" --amount-column="Total reward"
    """

    # Contains address -> AddressEntry mappings
    combined = collections.OrderedDict()
    errors = []
    book_keeping = collections.Counter()

    book_keeping["token_total"] = Decimal(0)
    book_keeping["uniq_entries"] = 0
    book_keeping["total_entries"] = 0

    for single_file in input_file:
        read_file(combined, errors, book_keeping, single_file, decimals, address_column, amount_column)

    # Write out valid combined output
    with open(output_file, 'w', newline='') as out:
        writer = csv.writer(out)
        writer.writerow([address_column, amount_column, "Non-rounded amount", "Count", "Sources", "Address forms"])

        for address, entry in combined.items():
            writer.writerow([
                to_checksum_address(address),
                str(entry.rounded_amount),
                str(entry.amount),
                entry.count,
                entry.sources,
                entry.address_forms,
            ])

    # Output errors to the user
    for file, line, error in errors:
        print("ERROR file:", file, "line:", line, "error:", error)

    print("Valid entries:", book_keeping["total_entries"])
    print("Unique entries:", book_keeping["uniq_entries"])
    print("Total distribution", book_keeping["token_total"], "tokens")
    print("Total distribution, raw approve() amount", int((book_keeping["token_total"] + 1) * 10**decimals), "tokens")
    print("Total", len(errors), "errors")

if __name__ == "__main__":
    main()
