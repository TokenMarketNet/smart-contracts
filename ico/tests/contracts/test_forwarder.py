"""Payment forwarder."""
import pytest

import uuid
from eth_utils import to_wei
from eth_tester.exceptions import TransactionFailed

from sha3 import keccak_256
from eth_utils import decode_hex


@pytest.fixture
def payment_forwarder(chain, team_multisig):
    args = [team_multisig, team_multisig]

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('PaymentForwarder', deploy_args=args, deploy_transaction=tx)
    return contract


def test_pay_once(web3, payment_forwarder, team_multisig, customer):
    """Pay for an address."""

    value = to_wei("1.0", "ether")
    customer_id = int(uuid.uuid4().hex, 16) # Customer ids are 128-bit UUID v4
    event_filter = payment_forwarder.events.PaymentForwarded().createFilter(fromBlock=0)
    team_multisig_begin = web3.eth.getBalance(team_multisig)
    payment_forwarder.functions.payWithoutChecksum(customer_id, customer).transact({"value": value, "from": customer})
    team_multisig_end = web3.eth.getBalance(team_multisig)

    assert team_multisig_end - team_multisig_begin > 0
    assert payment_forwarder.functions.totalTransferred().call() == value
    assert payment_forwarder.functions.paymentsByCustomer(customer_id).call() == value
    assert payment_forwarder.functions.customerCount().call() == 1

    # Check we properly generate an event
    events = event_filter.get_all_entries()
    assert len(events) == 1
    e = events[-1]
    assert e["args"]["source"] == customer
    assert e["args"]["amount"] == value
    assert e["args"]["customerId"] == customer_id
    assert e["args"]["benefactor"] == customer


def test_pay_twice(web3, payment_forwarder, team_multisig, customer, customer_2):
    """Pay for an address twice."""

    value = to_wei("1.0", "ether")
    customer_id = int(uuid.uuid4().hex, 16)  # Customer ids are 128-bit UUID v4
    event_filter = payment_forwarder.events.PaymentForwarded().createFilter(fromBlock=0)
    team_multisig_begin = web3.eth.getBalance(team_multisig)
    # We pay from two distinct addresses on behalf of the same customer
    checksumbyte = keccak_256(decode_hex(format(customer_id, 'x').zfill(32)) + decode_hex(format(customer[2:]).zfill(40))).digest()[:1]
    payment_forwarder.functions.pay(customer_id, customer, checksumbyte).transact({"value": value, "from": customer})

    # Here we make sure the first checkummed investment was successful
    events = event_filter.get_new_entries()
    assert len(events) == 1
    e = events[-1]
    assert e["args"]["source"] == customer
    assert e["args"]["amount"] == value
    assert e["args"]["customerId"] == customer_id
    assert e["args"]["benefactor"] == customer

    payment_forwarder.functions.payWithoutChecksum(customer_id, customer).transact({"value": value, "from": customer_2})
    team_multisig_end = web3.eth.getBalance(team_multisig)

    assert team_multisig_end - team_multisig_begin > 0
    assert payment_forwarder.functions.totalTransferred().call() == 2*value
    assert payment_forwarder.functions.paymentsByCustomer(customer_id).call() == 2*value
    assert payment_forwarder.functions.paymentsByBenefactor(customer).call() == 2*value
    assert payment_forwarder.functions.customerCount().call() == 1

    # Check we properly generate an event
    events = event_filter.get_new_entries()
    assert len(events) == 1
    e = events[-1]
    assert e["args"]["source"] == customer_2
    assert e["args"]["amount"] == value
    assert e["args"]["customerId"] == customer_id
    assert e["args"]["benefactor"] == customer


def test_pay_for_myself(web3, payment_forwarder, team_multisig, customer):
    """Pay for myself."""

    value = to_wei("1.0", "ether")
    customer_id = int(uuid.uuid4().hex, 16) # Customer ids are 128-bit UUID v4
    event_filter = payment_forwarder.events.PaymentForwarded().createFilter(fromBlock=0)
    team_multisig_begin = web3.eth.getBalance(team_multisig)

    checksumbyte = keccak_256(decode_hex(format(customer_id, 'x').zfill(32))).digest()[:1]
    payment_forwarder.functions.payForMyselfWithChecksum(customer_id, checksumbyte).transact({"value": value, "from": customer})
    team_multisig_end = web3.eth.getBalance(team_multisig)

    assert team_multisig_end - team_multisig_begin > 0
    assert payment_forwarder.functions.totalTransferred().call() == value
    assert payment_forwarder.functions.paymentsByCustomer(customer_id).call() == value
    assert payment_forwarder.functions.customerCount().call() == 1

    # Check we properly generate an event
    events = event_filter.get_new_entries()
    assert len(events) == 1
    e = events[-1]
    assert e["args"]["source"] == customer
    assert e["args"]["amount"] == value
    assert e["args"]["customerId"] == customer_id
    assert e["args"]["benefactor"] == customer


def test_halt(web3, payment_forwarder, team_multisig, customer):
    """We can stop crowdsale."""

    value = to_wei("1.0", "ether")
    customer_id = int(uuid.uuid4().hex, 16) # Customer ids are 128-bit UUID v4

    team_multisig_begin = web3.eth.getBalance(team_multisig)
    payment_forwarder.functions.halt().transact({"from": team_multisig})
    with pytest.raises(TransactionFailed):
        payment_forwarder.functions.payWithoutChecksum(customer_id, customer).transact({"value": value, "from": customer})


def test_unhalt(web3, payment_forwarder, team_multisig, customer):
    """We can resume crowdsale."""

    value = to_wei("1.0", "ether")
    customer_id = int(uuid.uuid4().hex, 16)  # Customer ids are 128-bit UUID v4

    payment_forwarder.functions.halt().transact({"from": team_multisig})
    payment_forwarder.functions.unhalt().transact({"from": team_multisig})

    assert payment_forwarder.functions.customerCount().call() == 0
    payment_forwarder.functions.payWithoutChecksum(customer_id, customer).transact({"value": value, "from": customer})
    assert payment_forwarder.functions.customerCount().call() == 1
