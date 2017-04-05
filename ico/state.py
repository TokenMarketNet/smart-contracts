from enum import IntEnum


class CrowdsaleState(IntEnum):
    """Match Crowdsale.State in the contract."""
    Unknown = 0
    Preparing = 1
    PreFunding = 2
    Funding = 3
    Success = 4
    Failure = 5
    Finalized = 6
    Refunding = 7


class UpgradeState(IntEnum):
    """Match UpgradeAgentEnabledToken.State in the contract."""
    Unknown = 0
    NotAllowed = 1
    WaitingForAgent = 2
    ReadyToUpgrade = 3
    Upgrading = 4


