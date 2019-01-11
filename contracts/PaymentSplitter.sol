/**
 * This smart contract code is Copyright 2018 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.18;

/**
 * @dev Split ether between parties.
 * @author TokenMarket Ltd. /  Ville Sundell <ville at tokenmarket.net>
 *
 * Allows splitting payments between parties.
 * Ethers are split to parties, each party has slices they are entitled to.
 * Ethers of this smart contract are divided into slices upon split().
 */

import "./Recoverable.sol";
import "zeppelin/contracts/math/SafeMath.sol";

contract PaymentSplitter is Recoverable {
  using SafeMath for uint256; // We use only uint256 for safety reasons (no boxing)

  /// @dev Describes a party (address and amount of slices the party is entitled to)
  struct Party {
    address addr;
    uint256 slices;
  }

  /// @dev This is just a failsafe, so we can't initialize a contract where
  ///      splitting would not be succesful in the future (for example because
  ///      of decreased block gas limit):
  uint256 constant MAX_PARTIES = 100;
  /// @dev How many slices there are in total:
  uint256 public totalSlices;
  /// @dev Array of "Party"s for each party's address and amount of slices:
  Party[] public parties;

  /// @dev This event is emitted when someone makes a payment:
  ///      (Gnosis MultiSigWallet compatible event)
  event Deposit(address indexed sender, uint256 value);
  /// @dev This event is emitted when someone splits the ethers between parties:
  ///      (emitted once per call)
  event Split(address indexed who, uint256 value);
  /// @dev This event is emitted for every party we send ethers to:
  event SplitTo(address indexed to, uint256 value);

  /// @dev Constructor: takes list of parties and their slices.
  /// @param addresses List of addresses of the parties
  /// @param slices Slices of the parties. Will be added to totalSlices.
  function PaymentSplitter(address[] addresses, uint[] slices) public {
    require(addresses.length == slices.length, "addresses and slices must be equal length.");
    require(addresses.length > 0 && addresses.length < MAX_PARTIES, "Amount of parties is either too many, or zero.");

    for(uint i=0; i<addresses.length; i++) {
      parties.push(Party(addresses[i], slices[i]));
      totalSlices = totalSlices.add(slices[i]);
    }
  }

  /// @dev Split the ethers, and send to parties according to slices.
  ///      This can be intentionally invoked by anyone: if some random person
  ///      wants to pay for the gas, that's good for us.
  function split() external {
    uint256 totalBalance = this.balance;
    uint256 slice = totalBalance.div(totalSlices);

    for(uint i=0; i<parties.length; i++) {
      uint256 amount = slice.mul(parties[i].slices);

      parties[i].addr.send(amount);
      emit SplitTo(parties[i].addr, amount);
    }

    emit Split(msg.sender, totalBalance);
  }

  /// @dev Fallback function, intentionally designed to fit to the gas stipend.
  function() public payable {
    emit Deposit(msg.sender, msg.value);
  }
}
