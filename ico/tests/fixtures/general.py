import pytest
from web3.contract import Contract


@pytest.fixture
def token_name() -> str:
    return "Unit test token"


@pytest.fixture
def token_symbol() -> str:
    return "TEST"


@pytest.fixture
def initial_supply() -> str:
    return 10000000


@pytest.fixture
def customer(web3, accounts) -> str:
    """Get a customer address."""
    return web3.toChecksumAddress(accounts[1])


@pytest.fixture
def customer_2(web3, accounts) -> str:
    """Get another customer address."""
    return web3.toChecksumAddress(accounts[2])


@pytest.fixture
def beneficiary(web3, accounts) -> str:
    """The team control address."""
    return web3.toChecksumAddress(accounts[3])


@pytest.fixture
def team_multisig(web3, accounts) -> str:
    """The team multisig address."""
    return web3.toChecksumAddress(accounts[4])


@pytest.fixture
def malicious_address(web3, accounts) -> str:
    """Somebody who tries to perform activities they are not allowed to."""
    return web3.toChecksumAddress(accounts[5])


@pytest.fixture
def empty_address(web3, accounts):
    """This account never holds anything."""
    return web3.toChecksumAddress(accounts[6])


@pytest.fixture
def allowed_party(web3, accounts):
    """Gets ERC-20 allowance."""
    return web3.toChecksumAddress(accounts[7])



#
# ERC-20 fixtures
#

@pytest.fixture
def token_owner(beneficiary):
    return beneficiary


@pytest.fixture
def token(chain, team_multisig, token_name, token_symbol, initial_supply) -> Contract:
    """Create the token contract."""

    args = [token_name, token_symbol, initial_supply, 0, True]  # Owner set

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('CrowdsaleToken', deploy_args=args, deploy_transaction=tx)
    return contract


@pytest.fixture
def empty_token(chain, team_multisig, token_name, token_symbol) -> Contract:
    """Create the token contract without initial supply."""

    args = [token_name, token_symbol, 0, 0, True]  # Owner set

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('CrowdsaleToken', deploy_args=args, deploy_transaction=tx)
    return contract
