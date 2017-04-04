"""Library extraction from deployed contracts."""
from populus.chain import TestRPCChain
from web3.contract import Contract

from ico.utils import get_libraries


def test_extract_libraries(chain: TestRPCChain, uncapped_flatprice: Contract):
    """We get library information of deployed contract."""

    libraries = get_libraries(chain, "UncappedCrowdsale", uncapped_flatprice)
    assert libraries["SafeMathLib"].startswith("0x")

