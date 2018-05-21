/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 *
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

pragma solidity ^0.4.18;

/**
 * @dev Forward Ethereum payments to two or more parties.
 *
 * Allows splitting payments between parties.
 */
contract PaymentSplitter {

  struct Part {
    address who;
    uint shares;
  }

  uint totalShares;
  Part[] public parts;

  function PaymentSplitter(address[] addresses, uint[] shares) public {
    for(uint i=0; i<addresses.length; i++) {
      parts.push(Part(addresses[i], shares[i]));
      totalShares += shares[i];
    }
  }

  function feedMe() external {

  }

  function() public {
    for(uint i=0; i<parts.length; i++) {
      parts[0].who;
    }
  }
}
