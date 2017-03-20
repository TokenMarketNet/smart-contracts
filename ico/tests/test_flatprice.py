"""Capped ICO."""
import datetime

import pytest
from eth_utils import to_wei
from ethereum.tester import TransactionFailed
from web3.contract import Contract



def test_flatprice_initialized(ico: Contract, preico_cap, team_multisig, preico_token_allocation):
    """PreICO is initialized with the parameters we want."""

    assert ico.call().owner() == team_multisig
    assert ico.call().getTokensLeft() == preico_token_allocation


