"""Payment forwarder."""
import pytest
import datetime

from eth_tester.exceptions import TransactionFailed
from web3.contract import Contract


@pytest.fixture
def token(chain, team_multisig) -> Contract:
    """Create the token contract."""

    args = [team_multisig, "Foobar", "FOOB", 1000000, 0, int((datetime.datetime(2017, 4, 22, 16, 0) - datetime.datetime(1970, 1, 1)).total_seconds())]

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('CentrallyIssuedToken', deploy_args=args, deploy_transaction=tx)

    contract.functions.releaseTokenTransfer().transact({"from": team_multisig})
    return contract


@pytest.fixture
def issue_script_owner(web3,  accounts):
    """Ethereum account that interacts with issuer contract."""
    return web3.toChecksumAddress(accounts[8])


@pytest.fixture
def issuer(chain, team_multisig, token, issue_script_owner):
    args = [issue_script_owner, team_multisig, token.address]

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('Issuer', deploy_args=args, deploy_transaction=tx)

    # Set issuance allowance
    assert token.functions.balanceOf(team_multisig).call() > 2000
    token.functions.approve(contract.address, 2000).transact({"from": team_multisig})

    return contract


def test_issue(web3, issuer, issue_script_owner, customer, token, team_multisig):
    """Issue some tokens."""

    team_multisig_begin = token.functions.balanceOf(team_multisig).call()
    assert token.functions.allowance(team_multisig, issuer.address).call() == 2000
    assert issuer.functions.owner().call() == issue_script_owner
    issuer.functions.issue(customer, 1000).transact({"from": issue_script_owner})
    assert issuer.functions.issuedCount().call() == 1000
    assert token.functions.balanceOf(customer).call() == 1000
    team_multisig_end = token.functions.balanceOf(team_multisig).call()
    assert team_multisig_begin - team_multisig_end == 1000


def test_issue_too_many(web3, issuer, issue_script_owner, customer):
    """Issue over allowance."""
    with pytest.raises(TransactionFailed):
        issuer.functions.issue(customer, 3000).transact({"from": issue_script_owner})


def test_issue_twice(web3, issuer, issue_script_owner, customer):
    """Issue some tokens."""
    issuer.functions.issue(customer, 500).transact({"from": issue_script_owner})
    with pytest.raises(TransactionFailed):
        issuer.transact({"from": issue_script_owner}).issue(customer, 500)


def test_issue_not_an_owner(web3, issuer, customer):
    """Somebody tries to issue for themselves."""
    with pytest.raises(TransactionFailed):
        issuer.functions.issue(customer, 500).transact({"from": customer})
