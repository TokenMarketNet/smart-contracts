pragma solidity ^0.4.6;

/**
 * Upgrade agent interface inspired by Lunyr.
 *
 *
 */
contract UpgradeAgent {
  address public owner;
  bool public isUpgradeAgent;
  function upgradeFrom(address _from, uint256 _value) public;
  function finalizeUpgrade() public;
  function setOriginalSupply() public;
}
