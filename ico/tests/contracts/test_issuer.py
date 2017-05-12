"""Payment forwarder."""
import pytest

from ethereum.tester import TransactionFailed
from web3.contract import Contract


@pytest.fixture
def token(chain, team_multisig) -> Contract:
    """Create the token contract."""

    args = [team_multisig, "Foobar", "FOOB", 1000000, 0]

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('CentrallyIssuedToken', deploy_args=args, deploy_transaction=tx)
    return contract


@pytest.fixture
def issue_script_owner(accounts):
    """Ethereum account that interacts with issuer contract."""
    return accounts[8]


@pytest.fixture
def issuer(chain, team_multisig, token, issue_script_owner):
    args = [issue_script_owner, team_multisig, token.address]

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('Issuer', deploy_args=args, deploy_transaction=tx)

    # Set issuance allowance
    assert token.call().balanceOf(team_multisig) > 2000
    token.transact({"from": team_multisig}).approve(contract.address, 2000)

    return contract


def test_issue(web3, issuer, issue_script_owner, customer, token, team_multisig):
    """Issue some tokens."""

    team_multisig_begin = token.call().balanceOf(team_multisig)
    assert token.call().allowance(team_multisig, issuer.address) == 2000
    assert issuer.call().owner() == issue_script_owner
    issuer.transact({"from": issue_script_owner}).issue(customer, 1000)
    assert issuer.call().issuedCount() == 1000
    assert token.call().balanceOf(customer) == 1000
    team_multisig_end = token.call().balanceOf(team_multisig)
    assert team_multisig_begin - team_multisig_end == 1000


def test_issue_too_many(web3, issuer, issue_script_owner, customer):
    """Issue over allowance."""
    with pytest.raises(TransactionFailed):
        issuer.transact({"from": issue_script_owner}).issue(customer, 3000)


def test_issue_twice(web3, issuer, issue_script_owner, customer):
    """Issue some tokens."""
    issuer.transact({"from": issue_script_owner}).issue(customer, 500)
    with pytest.raises(TransactionFailed):
        issuer.transact({"from": issue_script_owner}).issue(customer, 500)


def test_issue_not_an_owner(web3, issuer, customer):
    """Somebody tries to issue for themselves."""
    with pytest.raises(TransactionFailed):
        issuer.transact({"from": customer}).issue(customer, 500)
