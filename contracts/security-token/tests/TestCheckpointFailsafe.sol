pragma solidity ^0.4.18;

import "../CheckpointToken.sol";

contract TestCheckpointFailsafe {
  function getTokenBalance(CheckpointToken token, uint checkpointID, address who, uint index) public constant returns (bool result, uint balance, uint latestCheckpointID) {
    uint tmpCheckpointID;
    uint tmpBalance;

    (latestCheckpointID, balance) = token.tokenBalances(who, index);
    (tmpCheckpointID, tmpBalance) = token.tokenBalances(who, index+1);

    if (latestCheckpointID >= checkpointID && checkpointID < tmpCheckpointID) {
      result = true;
    } else {
      result = false;
    }
  }
}
