"""SecurityToken tests"""
import pytest
from random import randint
from web3.contract import Contract
from ico.tests.utils import check_gas
from ico.tests.utils import removeNonPrintable
from eth_utils import decode_hex, to_bytes
from eth_tester.exceptions import TransactionFailed


@pytest.fixture
def zero_address() -> str:
    return "0x0000000000000000000000000000000000000000"


@pytest.fixture
def security_token_name() -> str:
    return "SecurityToken"


@pytest.fixture
def security_token_symbol() -> str:
    return "SEC"


@pytest.fixture
def security_token_initial_supply() -> str:
    return 999999999000000000000000000


#
# ERC-20 fixtures
#
@pytest.fixture
def basic_kyc(chain, team_multisig) -> Contract:
    """Create the transaction verifier contract."""

    tx = {
        "from": team_multisig
    }

    contract, hash_ = chain.provider.deploy_contract('BasicKYC', deploy_transaction=tx)

    check_gas(chain, hash_)

    return contract


@pytest.fixture
def mock_security_transfer_agent(chain, team_multisig) -> Contract:
    """Create the transaction verifier contract."""

    tx = {
        "from": team_multisig
    }

    contract, hash_ = chain.provider.deploy_contract('MockSecurityTransferAgent', deploy_transaction=tx)

    check_gas(chain, hash_)

    return contract

@pytest.fixture
def restricted_transfer_agent(chain, team_multisig, basic_kyc) -> Contract:
    """Create the transaction verifier contract."""

    args = [basic_kyc.address]

    tx = {
        "from": team_multisig
    }

    contract, hash_ = chain.provider.deploy_contract('RestrictedTransferAgent', deploy_args=args, deploy_transaction=tx)

    check_gas(chain, hash_)

    return contract

@pytest.fixture
def advanced_transfer_agent(chain, team_multisig, basic_kyc) -> Contract:
    """Create the transaction verifier contract."""

    args = [basic_kyc.address]

    tx = {
        "from": team_multisig
    }

    contract, hash_ = chain.provider.deploy_contract('AdvancedTransferAgent', deploy_args=args, deploy_transaction=tx)

    check_gas(chain, hash_)

    return contract

@pytest.fixture
def security_token(chain, team_multisig, security_token_name, security_token_symbol, security_token_initial_supply) -> Contract:
    """Create the token contract."""

    args = [security_token_name, security_token_symbol]  # Owner set

    tx = {
        "from": team_multisig
    }

    contract, hash_ = chain.provider.deploy_contract('SecurityToken', deploy_args=args, deploy_transaction=tx)

    check_gas(chain, hash_)

    check_gas(chain, contract.transact(tx).addAddressToWhitelist(team_multisig))
    check_gas(chain, contract.transact(tx).issueTokens(security_token_initial_supply))

    assert contract.call().totalSupply() == security_token_initial_supply
    assert contract.call().balanceOf(team_multisig) == security_token_initial_supply

    return contract


def test_security_token_transaction_verifier(chain, security_token, mock_security_transfer_agent, team_multisig, customer):
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 10))
    assert security_token.call().balanceOf(customer) == 10

    check_gas(chain, security_token.transact({"from": team_multisig}).setTransactionVerifier(mock_security_transfer_agent.address))

    check_gas(chain, security_token.transact({"from": customer}).transfer(team_multisig, 10))
    assert security_token.call().balanceOf(customer) == 9


def test_security_token_freeze(chain, security_token, mock_security_transfer_agent, team_multisig, customer):
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 10))
    assert security_token.call().balanceOf(customer) == 10

    check_gas(chain, mock_security_transfer_agent.transact({"from": team_multisig}).freeze())
    check_gas(chain, security_token.transact({"from": team_multisig}).setTransactionVerifier(mock_security_transfer_agent.address))

    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": customer}).transfer(team_multisig, 10))

    assert security_token.call().balanceOf(customer) == 10


def test_restricted_transfer_agent_not_listed(chain, security_token, restricted_transfer_agent, team_multisig, customer):
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 10))
    assert security_token.call().balanceOf(customer) == 10

    check_gas(chain, security_token.transact({"from": team_multisig}).setTransactionVerifier(restricted_transfer_agent.address))

    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": customer}).transfer(team_multisig, 10))

    assert security_token.call().balanceOf(customer) == 10


def test_restricted_transfer_agent_whitelisted(chain, security_token, restricted_transfer_agent, team_multisig, customer, basic_kyc):
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 10))
    assert security_token.call().balanceOf(customer) == 10

    check_gas(chain, security_token.transact({"from": team_multisig}).setTransactionVerifier(restricted_transfer_agent.address))
    check_gas(chain, basic_kyc.transact({"from": team_multisig}).whitelistUser(team_multisig, True))

    check_gas(chain, security_token.transact({"from": customer}).transfer(team_multisig, 10))

    assert security_token.call().balanceOf(customer) == 0


def test_advanced_transfer_agent_whitelisted(chain, security_token, advanced_transfer_agent, team_multisig, customer, basic_kyc):
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 10))
    assert security_token.call().balanceOf(customer) == 10

    check_gas(chain, security_token.transact({"from": team_multisig}).setTransactionVerifier(advanced_transfer_agent.address))
    check_gas(chain, advanced_transfer_agent.transact({"from": team_multisig}).setWhitelist(team_multisig, True))

    check_gas(chain, security_token.transact({"from": customer}).transfer(team_multisig, 10))

    assert security_token.call().balanceOf(customer) == 0


def test_advanced_transfer_agent_blacklisted(chain, security_token, advanced_transfer_agent, team_multisig, customer, basic_kyc):
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 10))
    assert security_token.call().balanceOf(customer) == 10

    check_gas(chain, security_token.transact({"from": team_multisig}).setTransactionVerifier(advanced_transfer_agent.address))
    check_gas(chain, advanced_transfer_agent.transact({"from": team_multisig}).setBlacklist(team_multisig, True))

    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": customer}).transfer(team_multisig, 10))

    assert security_token.call().balanceOf(customer) == 10


def test_advanced_transfer_agent_whiteblacklisted(chain, security_token, advanced_transfer_agent, team_multisig, customer, basic_kyc):
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 10))
    assert security_token.call().balanceOf(customer) == 10

    check_gas(chain, security_token.transact({"from": team_multisig}).setTransactionVerifier(advanced_transfer_agent.address))
    check_gas(chain, advanced_transfer_agent.transact({"from": team_multisig}).setWhitelist(team_multisig, True))
    check_gas(chain, advanced_transfer_agent.transact({"from": team_multisig}).setBlacklist(team_multisig, True))

    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": customer}).transfer(team_multisig, 10))

    assert security_token.call().balanceOf(customer) == 10
