from enum import IntEnum


class CrowdsaleState(IntEnum):
    """Match Crowdsale.State in the contract."""
    Unknown = 0
    PreFunding = 1
    Funding = 2
    Success = 3
    Failure = 4
    Finalized = 5


class UpgradeState(IntEnum):
    """Match UpgradeAgentEnabledToken.State in the contract."""
    Unknown = 0
    NotAllowed = 1
    WaitingForAgent = 2
    ReadyToUpgrade = 3
    Upgrading = 4


