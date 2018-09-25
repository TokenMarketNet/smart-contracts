"""SecurityToken tests"""
import pytest
from random import randint
from web3.contract import Contract
from ico.tests.utils import check_gas
from ico.tests.utils import removeNonPrintable
from rlp.utils import decode_hex
from ethereum.tester import TransactionFailed
import time

@pytest.fixture
def testpayload() -> bytes:
    return decode_hex("a3e76c0f") # function receive() returns(bool)

@pytest.fixture
def announcement_name() -> str:
    return "Announcement 1"

@pytest.fixture
def announcement_uri() -> str:
    return "https://tokenmarket.net/"

@pytest.fixture
def announcement_type() -> int:
    return 123

@pytest.fixture
def announcement_hash() -> int:
    return 1234


@pytest.fixture
def announcement(chain, team_multisig, announcement_name, announcement_uri, announcement_type, announcement_hash) -> Contract:
    """Create a bogus announcement for testing"""

    args = [announcement_name, announcement_uri, announcement_type, announcement_hash]

    tx = {
        "from": team_multisig
    }

    contract, hash_ = chain.provider.deploy_contract('BogusAnnouncement', deploy_args=args, deploy_transaction=tx)


    check_gas(chain, hash_)

    assert removeNonPrintable(contract.call().announcementName()) == announcement_name
    assert removeNonPrintable(contract.call().announcementURI()) == announcement_uri
    assert contract.call().announcementType() == announcement_type

    return contract


@pytest.fixture
def receiver(chain, team_multisig) -> Contract:
    """Create the receiver contract for callback testing."""

    tx = {
        "from": team_multisig
    }

    contract, hash_ = chain.provider.deploy_contract('ERC827Receiver', deploy_transaction=tx)
    return contract


@pytest.fixture
def failsafetester(chain, team_multisig) -> Contract:
    """Create a contract for testing the failsafe."""

    tx = {
        "from": team_multisig
    }

    contract, hash_ = chain.provider.deploy_contract('TestCheckpointFailsafe', deploy_transaction=tx)
    return contract

@pytest.fixture
def security_token_name() -> str:
    return "SecurityToken"


@pytest.fixture
def security_token_symbol() -> str:
    return "SEC"


@pytest.fixture
def security_token_initial_supply() -> str:
    return 999999999000000000000000000

@pytest.fixture
def zero_address() -> str:
    return "0x0000000000000000000000000000000000000000"


#
# ERC-20 fixtures
#

@pytest.fixture
def security_token_verifier(chain, team_multisig) -> Contract:
    """Create the transaction verifier contract."""

    tx = {
        "from": team_multisig
    }

    contract, hash_ = chain.provider.deploy_contract('MockSecurityTransferAgent', deploy_transaction=tx)

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

def test_security_token_issue(chain, security_token, security_token_initial_supply, team_multisig, zero_address, customer):
    check_gas(chain, security_token.transact({"from": team_multisig}).issueTokens(security_token_initial_supply))
    assert security_token.call().totalSupply() == (security_token_initial_supply * 2)


def test_security_token_burn(chain, security_token, security_token_initial_supply, team_multisig, zero_address, customer):
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(security_token.address, security_token_initial_supply))
    check_gas(chain, security_token.transact({"from": team_multisig}).burnTokens(security_token_initial_supply - 1))
    assert security_token.call().totalSupply() == 1


def test_security_token_force(chain, security_token, security_token_initial_supply, team_multisig, zero_address, customer):
    assert security_token.call().balanceOf(team_multisig) == security_token_initial_supply
    check_gas(chain, security_token.transact({"from": team_multisig}).forceTransfer(team_multisig, customer, security_token_initial_supply))
    assert security_token.call().totalSupply() == security_token_initial_supply
    assert security_token.call().balanceOf(team_multisig) == 0
    assert security_token.call().balanceOf(customer) == security_token_initial_supply


def test_security_token_ask_balanceat(chain, security_token, security_token_initial_supply, team_multisig, zero_address, customer):
    check_gas(chain, security_token.transact().balanceAt(team_multisig, 1), gaslimit=26000)


def test_security_token_change_name_and_symbol(chain, security_token, security_token_initial_supply, team_multisig, zero_address, customer):
    check_gas(chain, security_token.transact({"from": team_multisig}).setTokenInformation("NewToken", "NEW"))
    assert security_token.call().name() == "NewToken"
    assert security_token.call().symbol() == "NEW"


def test_security_token_approve(chain, security_token, security_token_initial_supply, team_multisig, zero_address, customer):
    check_gas(chain, security_token.transact({"from": team_multisig}).approve(customer, security_token_initial_supply))
    assert security_token.call().allowance(team_multisig, customer) == security_token_initial_supply
    check_gas(chain, security_token.transact({"from": customer}).transferFrom(team_multisig, customer, security_token_initial_supply))
    assert security_token.call().balanceOf(team_multisig) == 0
    assert security_token.call().balanceOf(customer) == security_token_initial_supply


def test_security_token_approve_bad_amount(chain, security_token, security_token_initial_supply, team_multisig, zero_address, customer):
    check_gas(chain, security_token.transact({"from": team_multisig}).approve(customer, security_token_initial_supply))
    assert security_token.call().allowance(team_multisig, customer) == security_token_initial_supply
    with pytest.raises(TransactionFailed):
        security_token.transact({"from": customer}).transferFrom(team_multisig, customer, (security_token_initial_supply * 2))
    assert security_token.call().balanceOf(team_multisig) == security_token_initial_supply
    assert security_token.call().balanceOf(customer) == 0


def test_security_token_interface(security_token, token_owner: str, zero_address: str):
    """SecurityToken satisfies ERC-20/ERC-827 interface."""

    # https://github.com/OpenZeppelin/zeppelin-solidity/blob/master/contracts/token/ERC20.sol

    assert security_token.call().name() == "SecurityToken"
    assert security_token.call().symbol() == "SEC"
    assert security_token.call().decimals() == 18
    assert security_token.call().balanceOf(zero_address) == 0
    assert security_token.call().allowance(token_owner, zero_address) == 0

    # Event
    # We follow OpenZeppelin - in the ERO20 issue names are _from, _to, _value
    transfer = security_token._find_matching_event_abi("Transfer", ["from", "to", "value"])
    assert transfer

    approval = security_token._find_matching_event_abi("Approval", ["owner", "spender", "value"])
    assert approval


def test_security_token_transfer(chain, security_token, team_multisig, zero_address, customer):
    """Basic ERC-20 Transfer"""

    # https://github.com/OpenZeppelin/zeppelin-solidity/blob/master/contracts/token/ERC20.sol

    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 100), gaslimit=140000)
    assert security_token.call().balanceOf(customer) == 100
    assert security_token.call().balanceOf(zero_address) == 0
    assert security_token.call().balanceAt(customer, 1) == 0
    assert security_token.call().balanceAt(customer, 999999) == 100


def test_security_token_transfer_bad_amount(chain, security_token, team_multisig, zero_address, customer):
    """Basic ERC-20 Transfer"""
    original_balance = security_token.call().balanceOf(team_multisig)

    # https://github.com/OpenZeppelin/zeppelin-solidity/blob/master/contracts/token/ERC20.sol

    with pytest.raises(TransactionFailed):
        security_token.transact({"from": team_multisig}).transfer(customer, 10000000000000000000000000000000000)

    assert security_token.call().balanceOf(customer) == 0
    assert security_token.call().balanceOf(team_multisig) == original_balance


def test_security_token_transfer_stresstest(chain, security_token, team_multisig, zero_address, customer):
    """Basic ERC-20 Transfer"""

    # Feel free to raise the number of iterations according to your needs:
    # (These were run with fixed y = 1)
    # After 3 iterations, balanceAt() takes      25,177 gas each
    # After 3,000 iterations, balanceAt() takes  37,224 gas each
    # After 10,000 iterations, balanceAt() takes 39,780 gas each
    # Randomized 3,000 iterations (current) took 37,284 gas per transaction
    for x in range(3):
        check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 100))
        assert security_token.call().balanceOf(customer) == 100
        assert security_token.call().balanceOf(zero_address) == 0
        check_gas(chain, security_token.transact({"from": customer}).transfer(team_multisig, 100))
        y = 1+randint(0, x)
        check_gas(chain, security_token.transact().balanceAt(customer, y), tag=str(y))
        assert security_token.call().balanceOf(customer) == 0


def test_security_token_announce(chain, security_token, team_multisig, zero_address, customer, announcement, announcement_name, announcement_uri, announcement_type, announcement_hash):
    """Announce Announcement """
    security_token.transact({"from": team_multisig}).announce(announcement.address)

    events = security_token.pastEvents("Announced").get()
    assert len(events) == 1
    e = events[0]

    assert e["args"]["announcement"] == announcement.address
    assert removeNonPrintable(e["args"]["announcementName"]) == announcement_name
    assert removeNonPrintable(e["args"]["announcementURI"]) == announcement_uri
    assert e["args"]["announcementType"] == announcement_type
    assert e["args"]["announcementHash"] == announcement_hash


def test_security_token_erc827_allowance(security_token, team_multisig, testpayload, receiver, customer):
    """Testing succesful approve+transferFrom combination"""

    assert security_token.call().allowance(team_multisig, customer) == 0
    security_token.transact({"from": team_multisig}).approve(customer, 50, testpayload)
    assert security_token.call().allowance(team_multisig, customer) == 50
    security_token.transact({"from": team_multisig}).increaseApproval(customer, 100, testpayload)
    assert security_token.call().allowance(team_multisig, customer) == 150
    security_token.transact({"from": team_multisig}).decreaseApproval(customer, 50, testpayload)
    assert security_token.call().allowance(team_multisig, customer) == 100

    security_token.transact({"from": customer}).transferFrom(team_multisig, receiver.address, 100, testpayload)


def test_security_token_erc827_allowance_bad_amount(security_token, team_multisig, testpayload, receiver, customer):
    """Testing unsuccesful approve+transferFrom combination with too large amount"""

    assert security_token.call().allowance(team_multisig, customer) == 0
    security_token.transact({"from": team_multisig}).approve(customer, 50, testpayload)
    assert security_token.call().allowance(team_multisig, customer) == 50

    with pytest.raises(TransactionFailed):
        security_token.transact({"from": customer}).transferFrom(team_multisig, receiver.address, 100, testpayload)


def test_security_token_erc827_allowance_bad_claimant(security_token, team_multisig, testpayload, receiver, customer, customer_2):
    """Testing unsuccesful approve+transferFrom combination by 3rd party"""

    assert security_token.call().allowance(team_multisig, customer) == 0
    security_token.transact({"from": team_multisig}).approve(customer, 50, testpayload)
    assert security_token.call().allowance(team_multisig, customer) == 50

    with pytest.raises(TransactionFailed):
        security_token.transact({"from": customer_2}).transferFrom(team_multisig, receiver.address, 50, testpayload)


def test_security_token_erc827_allowance_without_approve(security_token, team_multisig, testpayload, receiver, customer, customer_2):
    """Testing succesful transferFrom without approve()"""

    assert security_token.call().allowance(team_multisig, customer) == 0

    with pytest.raises(TransactionFailed):
        security_token.transact({"from": customer}).transferFrom(team_multisig, receiver.address, 50, testpayload)


def test_security_token_erc827_transfer(security_token, team_multisig, testpayload, receiver):
    """Testing succesful token transfer"""
    assert security_token.call().balanceOf(receiver.address) == 0
    security_token.transact({"from": team_multisig}).transfer(receiver.address, 100, testpayload)
    assert security_token.call().balanceOf(receiver.address) == 100


def test_security_token_erc827_transfer_bad_amount(security_token, team_multisig, testpayload, receiver):
    """Testing unsuccesful token transfer with too large amount"""
    original_balance = security_token.call().balanceOf(team_multisig)

    assert security_token.call().balanceOf(receiver.address) == 0
    with pytest.raises(TransactionFailed):
        security_token.transact({"from": team_multisig}).transfer(receiver.address, 10000000000000000000000000000000000, testpayload)
    assert security_token.call().balanceOf(receiver.address) == 0
    assert security_token.call().balanceOf(team_multisig) == original_balance


def test_security_token_failsafe(chain, security_token, failsafetester, team_multisig, customer):
    """Basic ERC-20 Transfer"""
    index = 2

    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 1))
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 1))
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 1))
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 1))

    original_block, original_balance = security_token.call().tokenBalances(customer, index);

    tester_result, tester_balance, tester_block = failsafetester.call().getTokenBalance(security_token.address, original_block, customer, index);

    assert tester_result == True
    assert tester_balance == original_balance
    assert tester_block == original_block

    tester_result, tester_balance, tester_block = failsafetester.call().getTokenBalance(security_token.address, original_block, customer, 0);
    assert tester_result == False

    with pytest.raises(TransactionFailed):
        failsafetester.call().getTokenBalance(security_token.address, original_block, customer, 9999);

    # TODO: Report this bug to Populus when the source is public- The problem is the throw above, but happens only with this transaction:
    #security_token.transact({"from": team_multisig}).transfer(customer, 1)


def test_security_token_transaction_verifier(chain, security_token, security_token_verifier, team_multisig, customer):
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 10))
    assert security_token.call().balanceOf(customer) == 10

    check_gas(chain, security_token.transact({"from": team_multisig}).setTransactionVerifier(security_token_verifier.address))

    check_gas(chain, security_token.transact({"from": customer}).transfer(team_multisig, 10))
    assert security_token.call().balanceOf(customer) == 9


def test_security_token_freeze(chain, security_token, security_token_verifier, team_multisig, customer):
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 10))
    assert security_token.call().balanceOf(customer) == 10

    check_gas(chain, security_token_verifier.transact({"from": team_multisig}).freeze())
    check_gas(chain, security_token.transact({"from": team_multisig}).setTransactionVerifier(security_token_verifier.address))

    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": customer}).transfer(team_multisig, 10))

    assert security_token.call().balanceOf(customer) == 10
