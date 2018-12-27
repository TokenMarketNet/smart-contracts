pragma solidity ^0.4.18;

import "zeppelin/contracts/token/ERC20/ERC20.sol";
import "./ERC677.sol";


contract ERC677Token is ERC20, ERC677 {
  function transferAndCall(ERC677Receiver receiver, uint amount, bytes data) returns (bool success) {
    require(transfer(address(receiver), amount));

    ERC677Transfer(msg.sender, address(receiver), amount, data);

    require(receiver.tokenFallback(msg.sender, amount, data));
  }
}
