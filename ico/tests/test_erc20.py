"""ERC-20 compatibility."""

from web3.contract import Contract


def test_erc20_interface(token: Contract, token_owner: str, empty_address: str):
    """Token satisfies ERC-20 interface."""

    # https://github.com/OpenZeppelin/zeppelin-solidity/blob/master/contracts/token/ERC20.sol

    assert token.call().balanceOf(empty_address) == 0
    assert token.call().allowance(token_owner, empty_address) == 0

    # Event
    # We follow OpenZeppelin - in the ERO20 issue names are _from, _to, _value
    transfer = token._find_matching_event_abi("Transfer", ["from", "to", "value"])
    assert transfer

    approval = token._find_matching_event_abi("Approval", ["owner", "spender", "value"])
    assert approval
