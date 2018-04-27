pragma solidity ^0.4.18;

import "../CheckpointToken.sol";

contract TestCheckpointFailsafe {
  function getTokenBalance(CheckpointToken token, uint blockNumber, address who, uint index) public constant returns (bool result, uint balance, uint latestBlock) {
    uint tmpBlock;
    uint tmpBalance;

    (latestBlock, balance) = token.tokenBalances(who, index);
    (tmpBlock, tmpBalance) = token.tokenBalances(who, index+1);

    if (latestBlock >= blockNumber && blockNumber < tmpBlock) {
      result = true;
    } else {
      result = false;
    }
  }
}
