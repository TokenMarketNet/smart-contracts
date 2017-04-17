"""Rebuilding broken crowdsale contracts."""
import csv
from io import StringIO

import pytest
from web3.contract import Contract


@pytest.fixture
def sample_data():
    data = """
    Address,First payment at,Invested ETH,Received tokens
    0x88e26abf64015910315e5ea9cf28618cc00cfb92,2017-04-13T16:01:46+00:00,0.505,561
    0x1c5e4db864861d9b6203bd86af0c0b5ffcd6115d,2017-04-13T16:02:38+00:00,1.1,1361
    0x1f0b37c75bbf81e3f11977602b08bde3ba5a82b8,2017-04-13T16:04:33+00:00,29,32222
    0x00e35cd19466f310c70285d924cd0348bc60cbeb,2017-04-13T16:23:54+00:00,21,26111
    0x885dd0a8df8cbefaf7ed8b73709c00876356959b,2017-04-13T16:29:48+00:00,2.01942122,2386
    0x7b441389c743ea5785ab22af3736c23a0d2d9e6e,2017-04-13T16:29:48+00:00,1.2,1500
    0xba1eea15232a817a3ed7254368fed16208199e80,2017-04-13T17:09:04+00:00,0.995,1105
    0x771c664d953a481950af3050379250b3d0558069,2017-04-13T17:29:41+00:00,1.058916,1176
    0xba5c0929549419ebbe31403a3dc7a4af155b818f,2017-04-13T18:20:49+00:00,0.51555382,572
    0xac330613c8145147f7b7546b11083864edb2b5a5,2017-04-13T18:41:47+00:00,1.00634078,1118
    """.strip()
    return csv.DictReader(StringIO(data))


@pytest.fixture
def original_crowdsale(chain, team_multisig, start_time, end_time, milestone_pricing, preico_cap, minimum_funding_goal, cap, token) -> Contract:
    """Crowdsale that we are going to relaunch.."""

    args = [
        token.address,
        milestone_pricing.address,
        team_multisig,
        start_time,
        end_time,
        minimum_funding_goal,
        cap
    ]

    tx = {
        "from": team_multisig,
    }

    contract, hash = chain.provider.deploy_contract('MintedTokenCappedCrowdsale', deploy_args=args, deploy_transaction=tx)

    assert contract.call().owner() == team_multisig
    assert not token.call().released()
    assert contract.call().maximumSellableTokens() == cap

    # Allow crowdsale contract to do mint()
    token.transact({"from": team_multisig}).setMintAgent(contract.address, True)
    assert token.call().mintAgents(contract.address) == True

    return contract


@pytest.fixture
def relaunched_crowdsale(chain, team_multisig, start_time, end_time, milestone_pricing, preico_cap, minimum_funding_goal, cap, token) -> Contract:
    """Create a crowdsale with fixed contracts."""

    args = [
        token.address,
        milestone_pricing.address,
        team_multisig,
        start_time,
        end_time,
        minimum_funding_goal,
        cap
    ]

    tx = {
        "from": team_multisig,
    }

    contract, hash = chain.provider.deploy_contract('RelaunchedCrowdsale', deploy_args=args, deploy_transaction=tx)

    assert contract.call().owner() == team_multisig
    assert not token.call().released()
    assert contract.call().maximumSellableTokens() == cap

    # Allow crowdsale contract to do mint()
    token.transact({"from": team_multisig}).setMintAgent(contract.address, True)
    assert token.call().mintAgents(contract.address) == True

    return contract


def test_rebuild_failed_crowdsale(original_crowdsale, relaunched_crowdsale):
    """Rebuild a crowdsale that is not going to reach its minimum goal."""



