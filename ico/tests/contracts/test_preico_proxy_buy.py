"""Preico proxy buy."""
import datetime

import pytest
from eth_utils import from_wei
from eth_utils import to_wei
from ethereum.tester import TransactionFailed
from web3.contract import Contract

from ico.tests.utils import time_travel
from ico.utils import get_constructor_arguments
from ico.state import CrowdsaleState


@pytest.fixture()
def crowdsale(chain, presale_crowdsale, uncapped_token, team_multisig) -> Contract:
    """Crowdsale used intests.."""
    return presale_crowdsale


@pytest.fixture()
def token(chain, uncapped_token) -> Contract:
    """Token used in tests"""
    return uncapped_token
