/**
 * This smart contract code is Copyright 2018 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.18;

/**
 * @dev Send ethers with transfer()
 * @author TokenMarket Ltd. /  Ville Sundell <ville at tokenmarket.net>
 *
 * This is for testing will the fallback function of "target" fit to the
 * gas stipend.
 */

contract GasStipendTester {
  function transfer(address target) external payable {
    target.transfer(msg.value);
  }
}
