"""SecurityToken tests"""
import pytest
from random import randint
from web3.contract import Contract
from ico.tests.utils import check_gas
from ico.tests.utils import removeNonPrintable
from eth_utils import decode_hex, to_bytes
from eth_tester.exceptions import TransactionFailed
from eth_utils import keccak
from ico.sign import get_ethereum_address_from_private_key
from ico.sign import sign

@pytest.fixture
def monkey_patch_py_evm_gas_limit():
    # https://github.com/ethereum/eth - tester/issues/88
    # TODO: remove this once populus has been updated with latest eth-tester

    from eth_tester.backends.pyevm import main
    main.GENESIS_GAS_LIMIT = 999999999


@pytest.fixture
def chain(monkey_patch_py_evm_gas_limit, request):
    _chain = request.getfixturevalue('chain')
    return _chain


@pytest.fixture
def private_key():
    """Server side private key."""
    return "Lehma take over Cancuu tacos"


@pytest.fixture
def signer_address(private_key):
    """Server side signer address."""
    return get_ethereum_address_from_private_key(private_key)


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

    args = [to_bytes(text=announcement_name), to_bytes(text=announcement_uri), announcement_type, announcement_hash]

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

    contract, hash_ = chain.provider.deploy_contract('MockERC677Receiver', deploy_transaction=tx)
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
def security_token_url() -> str:
    return "http://tokenmarket.net/"

@pytest.fixture
def security_token_initial_supply() -> str:
    return 999999999000000000000000000


@pytest.fixture
def zero_address() -> str:
    return "0x0000000000000000000000000000000000000000"


@pytest.fixture
def voting_contract(chain, team_multisig, mock_kyc, security_token, security_token_verifier) -> Contract:
    """Create the Voting Contract."""

    # CheckpointToken _token, MockKYC _KYC, bytes32 name, bytes32 URI, uint256 _type, uint256 _hash, bytes32[] _options
    args = [
        security_token.address,
        mock_kyc.address,
        to_bytes(text="Voting X"),
        to_bytes(text="http://tokenmarket.net"),
        123,
        0,
        [to_bytes(text="Vested for voting")]
    ]

    tx = {
        "from": team_multisig
    }

    contract, hash_ = chain.provider.deploy_contract('VotingContract', deploy_args=args, deploy_transaction=tx)

    check_gas(chain, hash_)

    return contract


@pytest.fixture
def payout_contract(chain, team_multisig, mock_kyc, security_token, test_token, security_token_verifier) -> Contract:
    """Create the Voting Contract."""

    # CheckpointToken _token, MockKYC _KYC, bytes32 name, bytes32 URI, uint256 _type, uint256 _hash, bytes32[] _options
    # address, address, address, bytes32, bytes32, uint256, uint256, bytes32[]
    args = [
        security_token.address,
        test_token.address,
        mock_kyc.address,
        to_bytes(text="Pay X"),
        to_bytes(text="http://tokenmarket.net"),
        123,
        0,
        [to_bytes(text="Vested for dividend")]
    ]

    tx = {
        "from": team_multisig
    }

    contract, hash_ = chain.provider.deploy_contract('PayoutContract', deploy_args=args, deploy_transaction=tx)

    check_gas(chain, hash_)

    return contract

#
# ERC-20 fixtures
#

@pytest.fixture
def test_token(chain, team_multisig, token_name, token_symbol, security_token_initial_supply, release_agent, customer) -> Contract:
    """Create a Crowdsale token where transfer restrictions have been lifted."""

    args = [token_name, token_symbol, security_token_initial_supply, 18, True]  # Owner set

    tx = {
        "from": team_multisig
    }

    token, hash = chain.provider.deploy_contract('CrowdsaleToken', deploy_args=args, deploy_transaction=tx)

    token.transact({"from": team_multisig}).setReleaseAgent(team_multisig)
    token.transact({"from": team_multisig}).releaseTokenTransfer()

    return token


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
def mock_kyc(chain, team_multisig, customer) -> Contract:
    """Create the Mock KYC contract."""

    tx = {
        "from": team_multisig
    }

    contract, hash_ = chain.provider.deploy_contract('BasicKYC', deploy_transaction=tx)

    check_gas(chain, hash_)

    check_gas(chain, contract.transact(tx).adminAddRole(team_multisig, "setter"))
    check_gas(chain, contract.transact(tx).setAttributes(customer, 1))
    check_gas(chain, contract.transact(tx).setAttributes(team_multisig, 1))


    return contract


@pytest.fixture
def restricted_transfer_agent(chain, team_multisig, mock_kyc) -> Contract:
    """Create the transaction verifier contract."""
    args = [mock_kyc.address]

    tx = {
        "from": team_multisig
    }

    contract, hash_ = chain.provider.deploy_contract('RestrictedTransferAgent', deploy_args=args, deploy_transaction=tx)

    check_gas(chain, hash_)

    return contract


@pytest.fixture
def security_token(monkey_patch_py_evm_gas_limit, chain, team_multisig, security_token_name, security_token_symbol, security_token_url, security_token_initial_supply) -> Contract:
    """Create the token contract."""

    args = [security_token_name, security_token_symbol, security_token_url]  # Owner set

    tx = {
        "from": team_multisig,
        "gas": 9999999,
    }

    contract, hash_ = chain.provider.deploy_contract('SecurityToken', deploy_args=args, deploy_transaction=tx)

    check_gas(chain, hash_)

    check_gas(chain, contract.transact(tx).issueTokens(security_token_initial_supply))

    assert contract.call().totalSupply() == security_token_initial_supply
    assert contract.call().url() == security_token_url
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


def test_security_token_unauthorized(chain, security_token, team_multisig, customer, announcement, security_token_verifier):
    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": customer}).announce(announcement.address))
    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": customer}).forceTransfer(team_multisig, customer, 1))
    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": customer}).issueTokens(1))
    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": customer}).burnTokens(1))
    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": customer}).setTokenInformation("NOTUSED", "NOTUSED", "NOTUSED"))
    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": customer}).setTransactionVerifier(security_token_verifier.address))
    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": customer}).checkpoint())


def test_security_token_checkpoint(chain, security_token, team_multisig, customer):
    check_gas(chain, security_token.transact({"from": team_multisig}).checkpoint(), gaslimit=50000)


def test_security_token_ask_balanceat(chain, security_token, security_token_initial_supply, team_multisig, customer):
    initial_balance = security_token.call().balanceOf(team_multisig)
    check_gas(chain, security_token.transact({"from": team_multisig}).checkpoint())
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(security_token.address, security_token_initial_supply))
    check_gas(chain, security_token.transact({"from": team_multisig}).checkpoint())
    check_gas(chain, security_token.transact().balanceAt(team_multisig, 1), gaslimit=26500)

    historical_balance = security_token.call().balanceAt(team_multisig, 0)
    current_balance = security_token.call().balanceAt(team_multisig, 222)
    assert historical_balance == initial_balance
    assert security_token.call().balanceAt(team_multisig, 1) == security_token.call().balanceAt(team_multisig, 2)


def test_security_token_change_name_and_symbol(chain, security_token, security_token_initial_supply, team_multisig, zero_address, customer):
    check_gas(chain, security_token.transact({"from": team_multisig}).setTokenInformation("NewToken", "NEW", "http://new"))
    assert security_token.call().name() == "NewToken"
    assert security_token.call().symbol() == "NEW"
    assert security_token.call().url() == "http://new"


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
    """SecurityToken satisfies the ERC-20 interface."""

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

    check_gas(chain, security_token.transact({"from": team_multisig}).checkpoint())
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 100), gaslimit=140000)

    assert security_token.call().balanceOf(customer) == 100
    assert security_token.call().balanceOf(zero_address) == 0
    assert security_token.call().balanceAt(customer, 0) == 0
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
        check_gas(chain, security_token.transact().balanceAt(customer, y), tag=str(y),  gaslimit=30000)
        assert security_token.call().balanceOf(customer) == 0


def test_security_token_announce(chain, security_token, team_multisig, zero_address, customer, announcement, announcement_name, announcement_uri, announcement_type, announcement_hash):
    """Announce Announcement """
    assert security_token.call().announcementsByAddress(announcement.address) == 0
    security_token.transact({"from": team_multisig}).announce(announcement.address)

    events = security_token.events.Announced().createFilter(fromBlock=0).get_all_entries()
    assert len(events) == 1
    e = events[0]

    assert security_token.call().announcementsByAddress(announcement.address) == 1
    assert e["args"]["announcement"] == announcement.address
    assert removeNonPrintable(e["args"]["announcementName"]) == announcement_name
    assert removeNonPrintable(e["args"]["announcementURI"]) == announcement_uri
    assert e["args"]["announcementType"] == announcement_type
    assert e["args"]["announcementHash"] == announcement_hash


def test_security_token_erc677_transfer(security_token, team_multisig, testpayload, receiver):
    """Testing succesful token transfer"""
    assert security_token.call().balanceOf(receiver.address) == 0
    security_token.transact({"from": team_multisig}).transferAndCall(receiver.address, 100, testpayload)
    assert security_token.call().balanceOf(receiver.address) == 100


def test_security_token_failsafe(chain, security_token, failsafetester, team_multisig, customer):
    """Basic ERC-20 Transfer"""
    index = 2
    check_gas(chain, security_token.transact({"from": team_multisig}).checkpoint())
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 1))
    check_gas(chain, security_token.transact({"from": team_multisig}).checkpoint())
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 1))
    check_gas(chain, security_token.transact({"from": team_multisig}).checkpoint())
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 1))
    check_gas(chain, security_token.transact({"from": team_multisig}).checkpoint())
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


def test_voting_contract(chain, voting_contract, security_token, team_multisig, customer):
    check_gas(chain, voting_contract.transact({"from": team_multisig}).transferInvestorTokens(customer, 123))
    check_gas(chain, voting_contract.transact({"from": customer}).importInvestor(customer))
    check_gas(chain, voting_contract.transact({"from": customer}).act(123))
    return


def test_payout_contract(chain, payout_contract, security_token, test_token, team_multisig, customer):
    start_balance = test_token.call().balanceOf(team_multisig)
    assert start_balance > 0
    check_gas(chain, test_token.transact({"from": team_multisig}).approve(payout_contract.address, start_balance))
    check_gas(chain, payout_contract.transact({"from": customer}).fetchTokens())
    # check if tokens have been fetched
    assert test_token.functions.balanceOf(payout_contract.address).call() == start_balance

    # check tranfers
    initial_balance = test_token.call().balanceOf(team_multisig)
    check_gas(chain, payout_contract.transact({"from": team_multisig}).act(123))
    assert test_token.call().balanceOf(team_multisig) > initial_balance
    # check balance in payout contract
    # 0x0000000000000000000000000000000000000064 is default address(100)
    assert payout_contract.functions.balanceOf('0x0000000000000000000000000000000000000064').call()
    return


def test_erc865(chain, security_token, team_multisig, customer, private_key, signer_address):
    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(signer_address, 1234))

    token_addr = int(security_token.address, 16).to_bytes(20, byteorder="big")
    to_addr = int(team_multisig, 16).to_bytes(20, byteorder="big")
    value = int(123).to_bytes(32, byteorder="big")
    fee = int(123).to_bytes(32, byteorder="big")
    nonce = int(123).to_bytes(32, byteorder="big")
    prefix = int(0x48664c16).to_bytes(4, byteorder="big")
    payload = prefix + token_addr + to_addr + value + fee + nonce
    signed_data = sign(payload, private_key, hash_function=keccak)
    key_raw = signed_data["r_bytes"] + signed_data["s_bytes"] + signed_data["v"].to_bytes(1, byteorder="big")

    security_token.transact({"from": customer}).transferPreSigned(key_raw, team_multisig, 123, 123, 123)


def test_restricted_transfer_agent(chain, security_token, team_multisig, customer, restricted_transfer_agent, mock_kyc):
    check_gas(chain, security_token.transact({"from": team_multisig}).setTransactionVerifier(restricted_transfer_agent.address))

    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 10))
    assert security_token.call().balanceOf(customer) == 10

    check_gas(chain, mock_kyc.transact({"from": team_multisig}).setAttributes(customer, 0))

    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 10))

    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": customer}).transfer(team_multisig, 10))

    check_gas(chain, mock_kyc.transact({"from": team_multisig}).setAttributes(team_multisig, 2))

    check_gas(chain, security_token.transact({"from": team_multisig}).transfer(customer, 10))

    check_gas(chain, mock_kyc.transact({"from": team_multisig}).setAttributes(customer, 1))

    with pytest.raises(TransactionFailed):
        check_gas(chain, security_token.transact({"from": customer}).transfer(team_multisig, 10))

    check_gas(chain, mock_kyc.transact({"from": team_multisig}).setAttributes(team_multisig, 3))
    check_gas(chain, security_token.transact({"from": customer}).transfer(team_multisig, 10))
