from enum import IntEnum

from web3.testing import Testing

from populus.chain import TestRPCChain


class CrowdsaleState(IntEnum):
    """Match Crowdsale.State in the contract."""
    Unknown = 0
    PreFunding = 1
    Funding = 2
    Success = 3
    Failure = 4
    Finalized = 5


def time_travel(chain: TestRPCChain, timestamp: float):
    """Travel to a certain block in the future in chain."""
    web3 = chain.web3
    testing = Testing(web3)
    testing.timeTravel(timestamp)

