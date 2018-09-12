"""TAPAS tests"""
import pytest
from random import randint
from web3.contract import Contract
from ico.tests.utils import check_gas
from ico.tests.utils import removeNonPrintable
from rlp.utils import decode_hex
from ethereum.tester import TransactionFailed
import time

@pytest.fixture
def testpayload() -> str:
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

    contract, hash = chain.provider.deploy_contract('BogusTAPASAnnouncement', deploy_args=args, deploy_transaction=tx)


    check_gas(chain, hash)

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

    contract, hash = chain.provider.deploy_contract('ERC827Receiver', deploy_transaction=tx)
    return contract


@pytest.fixture
def failsafetester(chain, team_multisig) -> Contract:
    """Create a contract for testing the failsafe."""

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('TestCheckpointFailsafe', deploy_transaction=tx)
    return contract

@pytest.fixture
def tapas_token_name() -> str:
    return "TAPAS"


@pytest.fixture
def tapas_token_symbol() -> str:
    return "TAP"


@pytest.fixture
def tapas_initial_supply() -> str:
    return 999999999000000000000000000

@pytest.fixture
def zero_address() -> str:
    return "0x0000000000000000000000000000000000000000"


#
# ERC-20 fixtures
#

@pytest.fixture
def tapas_verifier(chain, team_multisig) -> Contract:
    """Create the transaction verifier contract."""

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('MockTransactionAgent', deploy_transaction=tx)

    check_gas(chain, hash)

    return contract

@pytest.fixture
def tapas_token(chain, team_multisig, tapas_token_name, tapas_token_symbol, tapas_initial_supply) -> Contract:
    """Create the token contract."""

    args = [tapas_token_name, tapas_token_symbol]  # Owner set

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('TAPASToken', deploy_args=args, deploy_transaction=tx)

    check_gas(chain, hash)

    check_gas(chain, contract.transact(tx).addAddressToWhitelist(team_multisig))
    check_gas(chain, contract.transact(tx).issueTokens(tapas_initial_supply))

    assert contract.call().totalSupply() == tapas_initial_supply
    assert contract.call().balanceOf(team_multisig) == tapas_initial_supply

    return contract

def test_tapas_issue(chain, tapas_token, tapas_initial_supply, team_multisig, zero_address, customer):
    check_gas(chain, tapas_token.transact({"from": team_multisig}).issueTokens(tapas_initial_supply))
    assert tapas_token.call().totalSupply() == (tapas_initial_supply * 2)


def test_tapas_burn(chain, tapas_token, tapas_initial_supply, team_multisig, zero_address, customer):
    check_gas(chain, tapas_token.transact({"from": team_multisig}).transfer(tapas_token.address, tapas_initial_supply))
    check_gas(chain, tapas_token.transact({"from": team_multisig}).burnTokens(tapas_initial_supply - 1))
    assert tapas_token.call().totalSupply() == 1


def test_tapas_force(chain, tapas_token, tapas_initial_supply, team_multisig, zero_address, customer):
    assert tapas_token.call().balanceOf(team_multisig) == tapas_initial_supply
    check_gas(chain, tapas_token.transact({"from": team_multisig}).forceTransfer(team_multisig, customer, tapas_initial_supply))
    assert tapas_token.call().totalSupply() == tapas_initial_supply
    assert tapas_token.call().balanceOf(team_multisig) == 0
    assert tapas_token.call().balanceOf(customer) == tapas_initial_supply


def test_tapas_ask_balanceat(chain, tapas_token, tapas_initial_supply, team_multisig, zero_address, customer):
    check_gas(chain, tapas_token.transact().balanceAt(team_multisig, 1), gaslimit=26000)


def test_tapas_change_name_and_symbol(chain, tapas_token, tapas_initial_supply, team_multisig, zero_address, customer):
    check_gas(chain, tapas_token.transact({"from": team_multisig}).setTokenInformation("NewToken", "NEW"))
    assert tapas_token.call().name() == "NewToken"
    assert tapas_token.call().symbol() == "NEW"


def test_tapas_approve(chain, tapas_token, tapas_initial_supply, team_multisig, zero_address, customer):
    check_gas(chain, tapas_token.transact({"from": team_multisig}).approve(customer, tapas_initial_supply))
    assert tapas_token.call().allowance(team_multisig, customer) == tapas_initial_supply
    check_gas(chain, tapas_token.transact({"from": customer}).transferFrom(team_multisig, customer, tapas_initial_supply))
    assert tapas_token.call().balanceOf(team_multisig) == 0
    assert tapas_token.call().balanceOf(customer) == tapas_initial_supply


def test_tapas_approve_bad_amount(chain, tapas_token, tapas_initial_supply, team_multisig, zero_address, customer):
    check_gas(chain, tapas_token.transact({"from": team_multisig}).approve(customer, tapas_initial_supply))
    assert tapas_token.call().allowance(team_multisig, customer) == tapas_initial_supply
    with pytest.raises(TransactionFailed):
        tapas_token.transact({"from": customer}).transferFrom(team_multisig, customer, (tapas_initial_supply * 2))
    assert tapas_token.call().balanceOf(team_multisig) == tapas_initial_supply
    assert tapas_token.call().balanceOf(customer) == 0


def test_tapas_token_interface(tapas_token, token_owner: str, zero_address: str):
    """TAPAS satisfies ERC-20/ERC-827 interface."""

    # https://github.com/OpenZeppelin/zeppelin-solidity/blob/master/contracts/token/ERC20.sol

    assert tapas_token.call().name() == "TAPAS"
    assert tapas_token.call().symbol() == "TAP"
    assert tapas_token.call().decimals() == 18
    assert tapas_token.call().balanceOf(zero_address) == 0
    assert tapas_token.call().allowance(token_owner, zero_address) == 0

    # Event
    # We follow OpenZeppelin - in the ERO20 issue names are _from, _to, _value
    transfer = tapas_token._find_matching_event_abi("Transfer", ["from", "to", "value"])
    assert transfer

    approval = tapas_token._find_matching_event_abi("Approval", ["owner", "spender", "value"])
    assert approval


def test_tapas_transfer(chain, tapas_token, team_multisig, zero_address, customer):
    """Basic ERC-20 Transfer"""

    # https://github.com/OpenZeppelin/zeppelin-solidity/blob/master/contracts/token/ERC20.sol

    check_gas(chain, tapas_token.transact({"from": team_multisig}).transfer(customer, 100), gaslimit=140000)
    assert tapas_token.call().balanceOf(customer) == 100
    assert tapas_token.call().balanceOf(zero_address) == 0
    assert tapas_token.call().balanceAt(customer, 1) == 0
    assert tapas_token.call().balanceAt(customer, 999999) == 100


def test_tapas_transfer_bad_amount(chain, tapas_token, team_multisig, zero_address, customer):
    """Basic ERC-20 Transfer"""
    original_balance = tapas_token.call().balanceOf(team_multisig)

    # https://github.com/OpenZeppelin/zeppelin-solidity/blob/master/contracts/token/ERC20.sol

    with pytest.raises(TransactionFailed):
        tapas_token.transact({"from": team_multisig}).transfer(customer, 10000000000000000000000000000000000)

    assert tapas_token.call().balanceOf(customer) == 0
    assert tapas_token.call().balanceOf(team_multisig) == original_balance


def test_tapas_transfer_stresstest(chain, tapas_token, team_multisig, zero_address, customer):
    """Basic ERC-20 Transfer"""

    # Feel free to raise the number of iterations according to your needs:
    # (These were run with fixed y = 1)
    # After 3 iterations, balanceAt() takes      25,177 gas each
    # After 3,000 iterations, balanceAt() takes  37,224 gas each
    # After 10,000 iterations, balanceAt() takes 39,780 gas each
    # Randomized 3,000 iterations (current) took 37,284 gas per transaction
    for x in range(3):
        check_gas(chain, tapas_token.transact({"from": team_multisig}).transfer(customer, 100))
        assert tapas_token.call().balanceOf(customer) == 100
        assert tapas_token.call().balanceOf(zero_address) == 0
        check_gas(chain, tapas_token.transact({"from": customer}).transfer(team_multisig, 100))
        y = 1+randint(0, x)
        check_gas(chain, tapas_token.transact().balanceAt(customer, y), tag=str(y))
        assert tapas_token.call().balanceOf(customer) == 0


def test_tapas_announce(chain, tapas_token, team_multisig, zero_address, customer, announcement, announcement_name, announcement_uri, announcement_type, announcement_hash):
    """Announce TAPASAnnouncement """
    tapas_token.transact({"from": team_multisig}).announce(announcement.address)

    events = tapas_token.pastEvents("Announced").get()
    assert len(events) == 1
    e = events[0]

    assert e["args"]["announcement"] == announcement.address
    assert removeNonPrintable(e["args"]["announcementName"]) == announcement_name
    assert removeNonPrintable(e["args"]["announcementURI"]) == announcement_uri
    assert e["args"]["announcementType"] == announcement_type
    assert e["args"]["announcementHash"] == announcement_hash


def test_tapas_erc827_allowance(tapas_token, team_multisig, testpayload, receiver, customer):
    """Testing succesful approve+transferFrom combination"""

    assert tapas_token.call().allowance(team_multisig, customer) == 0
    tapas_token.transact({"from": team_multisig}).approve(customer, 50, testpayload)
    assert tapas_token.call().allowance(team_multisig, customer) == 50
    tapas_token.transact({"from": team_multisig}).increaseApproval(customer, 100, testpayload)
    assert tapas_token.call().allowance(team_multisig, customer) == 150
    tapas_token.transact({"from": team_multisig}).decreaseApproval(customer, 50, testpayload)
    assert tapas_token.call().allowance(team_multisig, customer) == 100

    tapas_token.transact({"from": customer}).transferFrom(team_multisig, receiver.address, 100, testpayload)


def test_tapas_erc827_allowance_bad_amount(tapas_token, team_multisig, testpayload, receiver, customer):
    """Testing unsuccesful approve+transferFrom combination with too large amount"""

    assert tapas_token.call().allowance(team_multisig, customer) == 0
    tapas_token.transact({"from": team_multisig}).approve(customer, 50, testpayload)
    assert tapas_token.call().allowance(team_multisig, customer) == 50

    with pytest.raises(TransactionFailed):
        tapas_token.transact({"from": customer}).transferFrom(team_multisig, receiver.address, 100, testpayload)


def test_tapas_erc827_allowance_bad_claimant(tapas_token, team_multisig, testpayload, receiver, customer, customer_2):
    """Testing unsuccesful approve+transferFrom combination by 3rd party"""

    assert tapas_token.call().allowance(team_multisig, customer) == 0
    tapas_token.transact({"from": team_multisig}).approve(customer, 50, testpayload)
    assert tapas_token.call().allowance(team_multisig, customer) == 50

    with pytest.raises(TransactionFailed):
        tapas_token.transact({"from": customer_2}).transferFrom(team_multisig, receiver.address, 50, testpayload)


def test_tapas_erc827_allowance_without_approve(tapas_token, team_multisig, testpayload, receiver, customer, customer_2):
    """Testing succesful transferFrom without approve()"""

    assert tapas_token.call().allowance(team_multisig, customer) == 0

    with pytest.raises(TransactionFailed):
        tapas_token.transact({"from": customer}).transferFrom(team_multisig, receiver.address, 50, testpayload)


def test_tapas_erc827_transfer(tapas_token, team_multisig, testpayload, receiver):
    """Testing succesful token transfer"""
    assert tapas_token.call().balanceOf(receiver.address) == 0
    tapas_token.transact({"from": team_multisig}).transfer(receiver.address, 100, testpayload)
    assert tapas_token.call().balanceOf(receiver.address) == 100


def test_tapas_erc827_transfer_bad_amount(tapas_token, team_multisig, testpayload, receiver):
    """Testing unsuccesful token transfer with too large amount"""
    original_balance = tapas_token.call().balanceOf(team_multisig)

    assert tapas_token.call().balanceOf(receiver.address) == 0
    with pytest.raises(TransactionFailed):
        tapas_token.transact({"from": team_multisig}).transfer(receiver.address, 10000000000000000000000000000000000, testpayload)
    assert tapas_token.call().balanceOf(receiver.address) == 0
    assert tapas_token.call().balanceOf(team_multisig) == original_balance


def test_tapas_failsafe(chain, tapas_token, failsafetester, team_multisig, customer):
    """Basic ERC-20 Transfer"""
    index = 2

    check_gas(chain, tapas_token.transact({"from": team_multisig}).transfer(customer, 1))
    check_gas(chain, tapas_token.transact({"from": team_multisig}).transfer(customer, 1))
    check_gas(chain, tapas_token.transact({"from": team_multisig}).transfer(customer, 1))
    check_gas(chain, tapas_token.transact({"from": team_multisig}).transfer(customer, 1))

    original_block, original_balance = tapas_token.call().tokenBalances(customer, index);

    tester_result, tester_balance, tester_block = failsafetester.call().getTokenBalance(tapas_token.address, original_block, customer, index);

    assert tester_result == True
    assert tester_balance == original_balance
    assert tester_block == original_block

    tester_result, tester_balance, tester_block = failsafetester.call().getTokenBalance(tapas_token.address, original_block, customer, 0);
    assert tester_result == False

    with pytest.raises(TransactionFailed):
        failsafetester.call().getTokenBalance(tapas_token.address, original_block, customer, 9999);

    # TODO: Report this bug to Populus when the source is public- The problem is the throw above, but happens only with this transaction:
    #tapas_token.transact({"from": team_multisig}).transfer(customer, 1)


def test_tapas_transaction_verifier(chain, tapas_token, tapas_verifier, team_multisig, customer):
    check_gas(chain, tapas_token.transact({"from": team_multisig}).transfer(customer, 10))
    assert tapas_token.call().balanceOf(customer) == 10

    check_gas(chain, tapas_token.transact({"from": team_multisig}).setTransactionVerifier(tapas_verifier.address))

    check_gas(chain, tapas_token.transact({"from": customer}).transfer(team_multisig, 10))
    assert tapas_token.call().balanceOf(customer) == 9
