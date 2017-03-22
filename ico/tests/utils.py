from populus.chain import TestRPCChain
from web3.testing import Testing


def time_travel(chain: TestRPCChain, timestamp: float):
    """Travel to a certain block in the future in chain."""
    web3 = chain.web3
    testing = Testing(web3)
    testing.timeTravel(timestamp)
