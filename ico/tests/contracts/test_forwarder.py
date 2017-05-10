"""Payment forwarder."""
import pytest

import uuid
from eth_utils import to_wei
from ethereum.tester import TransactionFailed


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

    team_multisig_begin = web3.eth.getBalance(team_multisig)
    payment_forwarder.transact({"value": value, "from": customer}).pay(customer_id, customer)
    team_multisig_end = web3.eth.getBalance(team_multisig)

    assert team_multisig_end - team_multisig_begin > 0
    assert payment_forwarder.call().totalTransferred() == value
    assert payment_forwarder.call().paymentsByCustomer(customer_id) == value
    assert payment_forwarder.call().customerCount() == 1

    # Check we properly generate an event
    events = payment_forwarder.pastEvents("PaymentForwarded").get()
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

    team_multisig_begin = web3.eth.getBalance(team_multisig)
    # We pay from two distinct addresses on behalf of the same customer
    payment_forwarder.transact({"value": value, "from": customer}).pay(customer_id, customer)
    payment_forwarder.transact({"value": value, "from": customer_2}).pay(customer_id, customer)
    team_multisig_end = web3.eth.getBalance(team_multisig)

    assert team_multisig_end - team_multisig_begin > 0
    assert payment_forwarder.call().totalTransferred() == 2*value
    assert payment_forwarder.call().paymentsByCustomer(customer_id) == 2*value
    assert payment_forwarder.call().paymentsByBenefactor(customer) == 2*value
    assert payment_forwarder.call().customerCount() == 1

    # Check we properly generate an event
    events = payment_forwarder.pastEvents("PaymentForwarded").get()
    assert len(events) == 2
    e = events[-1]
    assert e["args"]["source"] == customer_2
    assert e["args"]["amount"] == value
    assert e["args"]["customerId"] == customer_id
    assert e["args"]["benefactor"] == customer


def test_pay_for_myself(web3, payment_forwarder, team_multisig, customer):
    """Pay for myself."""

    value = to_wei("1.0", "ether")
    customer_id = int(uuid.uuid4().hex, 16) # Customer ids are 128-bit UUID v4

    team_multisig_begin = web3.eth.getBalance(team_multisig)
    payment_forwarder.transact({"value": value, "from": customer}).payForMyself(customer_id)
    team_multisig_end = web3.eth.getBalance(team_multisig)

    assert team_multisig_end - team_multisig_begin > 0
    assert payment_forwarder.call().totalTransferred() == value
    assert payment_forwarder.call().paymentsByCustomer(customer_id) == value
    assert payment_forwarder.call().customerCount() == 1

    # Check we properly generate an event
    events = payment_forwarder.pastEvents("PaymentForwarded").get()
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
    payment_forwarder.transact({"from": team_multisig}).halt()
    with pytest.raises(TransactionFailed):
        payment_forwarder.transact({"value": value, "from": customer}).pay(customer_id, customer)


def test_unhalt(web3, payment_forwarder, team_multisig, customer):
    """We can resume crowdsale."""

    value = to_wei("1.0", "ether")
    customer_id = int(uuid.uuid4().hex, 16) # Customer ids are 128-bit UUID v4

    payment_forwarder.transact({"from": team_multisig}).halt()
    payment_forwarder.transact({"from": team_multisig}).unhalt()

    assert payment_forwarder.call().customerCount() == 0
    payment_forwarder.transact({"value": value, "from": customer}).pay(customer_id, customer)
    assert payment_forwarder.call().customerCount() == 1


