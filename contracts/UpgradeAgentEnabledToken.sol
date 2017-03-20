pragma solidity ^0.4.8;

import "zeppelin/contracts/token/ERC20.sol";
import "zeppelin/contracts/token/StandardToken.sol";
import "zeppelin/contracts/SafeMath.sol"; // TODO: Convert to SafeMathLib
import "./UpgradeAgent.sol";

/**
 * A token upgrade mechanism where users can opt-in amount of tokens to the next smart contract revision.
 *
 *
 * First envisioned by Golem and Lunyr.
 */
contract UpgradeAgentEnabledToken is StandardToken {

  // Upgrade information
  bool public finalizedUpgrade = false;
  address public upgradeMaster;
  UpgradeAgent public upgradeAgent;
  uint256 public totalUpgraded;

  event Upgrade(address indexed _from, address indexed _to, uint256 _value);
  event Refund(address indexed _from, uint256 _value);
  event UpgradeFinalized(address sender, address upgradeAgent);
  event UpgradeAgentSet(address agent);

  // TODO

  /**
   * Child contract must override this to define when upgrade is allowed.
   *
   */
  modifier canUpgrade() {
    _;
  }

}
