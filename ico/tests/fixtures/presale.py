import datetime

import pytest
from eth_utils import to_wei
from web3.contract import Contract


@pytest.fixture
def presale_freeze_ends_at() -> int:
    """How long presale funds stay frozen until refund."""
    return int(datetime.datetime(2017, 1, 1).timestamp())


@pytest.fixture
def presale_fund_collector(chain, presale_freeze_ends_at, team_multisig) -> Contract:
    """In actual ICO, the price is doubled (for testing purposes)."""
    args = [
        team_multisig,
        presale_freeze_ends_at,
        to_wei(1, "ether")
    ]
    tx = {
        "from": team_multisig,
    }
    presale_fund_collector, hash = chain.provider.deploy_contract('PresaleFundCollector', deploy_args=args, deploy_transaction=tx)
    return presale_fund_collector


@pytest.fixture
def presale_crowdsale(chain, presale_fund_collector, uncapped_flatprice, team_multisig):
    """ICO associated with the presale where funds will be moved to a presale."""
    presale_fund_collector.transact({"from": team_multisig}).setCrowdsale(uncapped_flatprice.address)
    return uncapped_flatprice
