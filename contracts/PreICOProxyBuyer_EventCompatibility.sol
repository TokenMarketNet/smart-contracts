/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.6;

/**
 * ABI compatibility shim to get.
 *
 * You can use this shim to get events out of old PreICOProxyBuyer contracts.
 */
contract PreICOProxyBuyer_EventCompatibility {

  /** Somebody loaded their investment money */
  event Invested(address investor, uint weiAmount, uint128 customerId);

}
