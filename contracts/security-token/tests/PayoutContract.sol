pragma solidity ^0.4.18;

import "./InvestorInteractionContract.sol";

contract PayoutContract is InvestorInteractionContract {
  ERC20 payoutToken;
  address from;
  uint256 initialBalance;
  uint256 oneUnit;

  function PayoutContract(ERC20 _payoutToken) {
    from = msg.sender;
    payoutToken = _payoutToken;
  }

  function fetchTokens(address from, uint256 amount) public {
    require(initialBalance == 0);

    uint256 allowed = payoutToken.allowance(from, address(this));
    payoutToken.transferFrom(from, address(this), allowed);

    initialBalance = allowed;
    oneUnit = initialBalance / maximumSupply;
  }

  // ACT??
  function act(uint256 votes) {
    require(oneUnit > 0);
    require(votes <= balanceOf(msg.sender));

    payoutToken.transfer(msg.sender, oneUnit * votes);
  }
}
