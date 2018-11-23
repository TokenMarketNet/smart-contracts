"""Releasable AMLToken token."""

import pytest
from eth_tester.exceptions import TransactionFailed
from web3.contract import Contract


def test_transfer_to_owner(aml_token: Contract, team_multisig: str, malicious_address: str, empty_address: str):
    """Only owner can move tokens back to him before releasing."""

    starting_amount = aml_token.functions.balanceOf(team_multisig).call()

    aml_token.functions.setTransferAgent(team_multisig, True).transact({"from": team_multisig})
    aml_token.functions.transfer(malicious_address, 1000000).transact({"from": team_multisig})

    assert starting_amount != aml_token.functions.balanceOf(team_multisig).call()

    aml_token.functions.transferToOwner(malicious_address).transact({"from": team_multisig})

    aml_token.functions.setReleaseAgent(team_multisig).transact({"from": team_multisig})
    aml_token.functions.releaseTokenTransfer().transact({"from": team_multisig})

    assert starting_amount == aml_token.functions.balanceOf(team_multisig).call()


def test_transfer_to_owner_after_release(aml_token: Contract, team_multisig: str, malicious_address: str, empty_address: str):
    """Only owner can move tokens back to him before releasing."""

    aml_token.functions.setReleaseAgent(team_multisig).transact({"from": team_multisig})
    aml_token.functions.releaseTokenTransfer().transact({"from": team_multisig})

    aml_token.functions.transfer(malicious_address, 1000000).transact({"from": team_multisig})

    with pytest.raises(TransactionFailed):
        aml_token.functions.transferToOwner(malicious_address).transact({"from": team_multisig})


def test_transfer_to_owner_only_owner(aml_token: Contract, team_multisig: str, malicious_address: str, empty_address: str):
    """Other parties cannot do AML reclaim."""

    starting_amount = aml_token.functions.balanceOf(team_multisig).call()

    aml_token.functions.setTransferAgent(team_multisig, True).transact({"from": team_multisig})
    aml_token.functions.transfer(malicious_address, 1000000).transact({"from": team_multisig})

    assert starting_amount != aml_token.functions.balanceOf(team_multisig).call()

    with pytest.raises(TransactionFailed):
        aml_token.functions.transferToOwner(malicious_address).transact({"from": malicious_address})
