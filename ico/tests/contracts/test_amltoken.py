"""Releasable AMLToken token."""

import pytest
from ethereum.tester import TransactionFailed
from web3.contract import Contract


def test_transfer_to_owner(aml_token: Contract, team_multisig: str, malicious_address: str, empty_address: str):
    """Only owner can move tokens back to him before releasing."""

    starting_amount = aml_token.call().balanceOf(team_multisig)

    aml_token.transact({"from": team_multisig}).setTransferAgent(team_multisig, True)
    aml_token.transact({"from": team_multisig}).transfer(malicious_address, 1000000)

    assert starting_amount != aml_token.call().balanceOf(team_multisig)

    aml_token.transact({"from": team_multisig}).transferToOwner(malicious_address)

    aml_token.transact({"from": team_multisig}).setReleaseAgent(team_multisig)
    aml_token.transact({"from": team_multisig}).releaseTokenTransfer()

    assert starting_amount == aml_token.call().balanceOf(team_multisig)


def test_transfer_to_owner_after_release(aml_token: Contract, team_multisig: str, malicious_address: str, empty_address: str):
    """Only owner can move tokens back to him before releasing."""

    aml_token.transact({"from": team_multisig}).setReleaseAgent(team_multisig)
    aml_token.transact({"from": team_multisig}).releaseTokenTransfer()

    aml_token.transact({"from": team_multisig}).transfer(malicious_address, 1000000)

    with pytest.raises(TransactionFailed):
        aml_token.transact({"from": team_multisig}).transferToOwner(malicious_address)


def test_transfer_to_owner_only_owner(aml_token: Contract, team_multisig: str, malicious_address: str, empty_address: str):
    """Other parties cannot do AML reclaim."""

    starting_amount = aml_token.call().balanceOf(team_multisig)

    aml_token.transact({"from": team_multisig}).setTransferAgent(team_multisig, True)
    aml_token.transact({"from": team_multisig}).transfer(malicious_address, 1000000)

    assert starting_amount != aml_token.call().balanceOf(team_multisig)

    with pytest.raises(TransactionFailed):
        aml_token.transact({"from": malicious_address}).transferToOwner(malicious_address)
