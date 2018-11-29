""" Test PaymentSplitter """

import enum
import pytest
from eth_tester.exceptions import TransactionFailed
from ico.tests.utils import time_travel
from ico.tests.utils import check_gas
from web3.contract import Contract


@pytest.fixture
def gas_stipend_tester(chain) -> Contract:
    """A test fixture to deploy a GasStipendTester."""

    contract, hash = chain.provider.deploy_contract('GasStipendTester')
    return contract


@pytest.fixture
def payment_splitter(chain, team_multisig, customer, customer_2) -> Contract:
    """A test fixture to deploy a PaymentSplitter."""

    args = [
        [customer, customer_2],
        [1, 1]
    ]

    contract, hash = chain.provider.deploy_contract('PaymentSplitter', deploy_args=args)
    return contract


@pytest.fixture
def payment_splitter_multiparty(chain, malicious_address, customer, customer_2) -> Contract:
    """A test fixture to deploy a PaymentSplitter."""

    args = [
        [customer, customer_2, malicious_address],
        [1, 1, 1]
    ]

    contract, hash = chain.provider.deploy_contract('PaymentSplitter', deploy_args=args)
    return contract


def test_payment_splitter_even(chain, payment_splitter, team_multisig, customer, customer_2):
    """ Testing basic splitting """
    w3 = chain.web3

    customer_initial_balance = w3.eth.getBalance(customer)
    customer_2_initial_balance = w3.eth.getBalance(customer_2)

    check_gas(chain, w3.eth.sendTransaction({"value": 2, "from": team_multisig, "to": payment_splitter.address, "gas": 23000}))
    assert w3.eth.getBalance(payment_splitter.address) == 2
    assert w3.eth.getBalance(customer) == customer_initial_balance
    assert w3.eth.getBalance(customer_2) == customer_2_initial_balance
    check_gas(chain, payment_splitter.transact({"from": team_multisig}).split())

    assert w3.eth.getBalance(payment_splitter.address) == 0
    assert w3.eth.getBalance(customer) == customer_initial_balance + 1
    assert w3.eth.getBalance(customer_2) == customer_2_initial_balance + 1


def test_payment_splitter_odd(chain, payment_splitter, team_multisig, customer, customer_2):
    """ Testing basic splitting """
    w3 = chain.web3

    customer_initial_balance = w3.eth.getBalance(customer)
    customer_2_initial_balance = w3.eth.getBalance(customer_2)

    check_gas(chain, w3.eth.sendTransaction({"value": 1, "from": team_multisig, "to": payment_splitter.address, "gas": 23000}))
    assert w3.eth.getBalance(payment_splitter.address) == 1
    assert w3.eth.getBalance(customer) == customer_initial_balance
    assert w3.eth.getBalance(customer_2) == customer_2_initial_balance
    check_gas(chain, payment_splitter.transact({"from": team_multisig}).split())

    assert w3.eth.getBalance(payment_splitter.address) == 1
    assert w3.eth.getBalance(customer) == customer_initial_balance
    assert w3.eth.getBalance(customer_2) == customer_2_initial_balance


def test_payment_splitter_multiparty(chain, payment_splitter_multiparty, team_multisig, malicious_address, customer, customer_2):
    """ Testing multiparty splitting """
    w3 = chain.web3

    customer_initial_balance = w3.eth.getBalance(customer)
    customer_2_initial_balance = w3.eth.getBalance(customer_2)
    malicious_address_initial_balance = w3.eth.getBalance(malicious_address)


    check_gas(chain, w3.eth.sendTransaction({"value": 100, "from": team_multisig, "to": payment_splitter_multiparty.address, "gas": 23000}))

    assert w3.eth.getBalance(payment_splitter_multiparty.address) == 100
    assert w3.eth.getBalance(malicious_address) == malicious_address_initial_balance
    assert w3.eth.getBalance(customer) == customer_initial_balance
    assert w3.eth.getBalance(customer_2) == customer_2_initial_balance
    check_gas(chain, payment_splitter_multiparty.transact({"from": team_multisig}).split())

    assert w3.eth.getBalance(payment_splitter_multiparty.address) == 1
    assert w3.eth.getBalance(malicious_address) == malicious_address_initial_balance + 33
    assert w3.eth.getBalance(customer) == customer_initial_balance + 33
    assert w3.eth.getBalance(customer_2) == customer_2_initial_balance + 33


def test_payment_splitter_zero(chain, payment_splitter, team_multisig, customer, customer_2):
    """ Testing basic splitting """
    w3 = chain.web3

    customer_initial_balance = w3.eth.getBalance(customer)
    customer_2_initial_balance = w3.eth.getBalance(customer_2)

    assert w3.eth.getBalance(payment_splitter.address) == 0
    check_gas(chain, payment_splitter.transact({"from": team_multisig}).split())

    assert w3.eth.getBalance(payment_splitter.address) == 0
    assert w3.eth.getBalance(customer) == customer_initial_balance
    assert w3.eth.getBalance(customer_2) == customer_2_initial_balance


def test_gas_stipend(chain, payment_splitter, team_multisig, gas_stipend_tester):
    """ Testing that the fallback fits to the gas stipend """
    w3 = chain.web3

    gas_stipend_tester.transact({"from": team_multisig, "gas": 33000, "value": 1}).transfer(payment_splitter.address)

    assert w3.eth.getBalance(payment_splitter.address) == 1
