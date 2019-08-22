/**
 * This smart contract code is Copyright 2018, 2019 TokenMarket Ltd. For more information see https://tokenmarket.net
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 * NatSpec is used intentionally to cover also other than public functions.
 * Solidity 0.4.18 is intentionally used: it's stable, and our framework is
 * based on that.
 */

pragma solidity ^0.4.24;

import "./CheckpointToken.sol";

contract ERC20SnapshotMixin is CheckpointToken {
  /// @dev This event is emitted upon snapshot creation (source: ERC20Snapshot)
  event Snapshot(uint256 id);

  /**
   * @dev This is implemented for the past and future compatibility.
   *
   * It is likely that the final ERC20Snapshot from Zeppelin will use this
   * function to lookup balances, since this is also used by eralier
   * MiniMeToken, pioneering the concept ERC20Snapshot and our CheckpoinToken
   * is based on.
   *
   * @param account Account address whose balance will be queried
   * @param snapshotId Snapshot ID (in our implementation CheckpointID)
   * @return Balance of `account` at `snapshotId`
   */
  function balanceOfAt(address account, uint256 snapshotId) external view returns (uint256) {
    return balanceAt(account, snapshotId);
  }
}
