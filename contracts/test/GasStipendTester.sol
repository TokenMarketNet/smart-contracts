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

contract GasStipendTester {
  function transfer(address target) external payable {
    target.transfer(msg.value);
  }
}
