pragma solidity ^0.4.18;

import "./InvestorInteractionContract.sol";
import "../KYCInterface.sol";

contract PayoutContract is InvestorInteractionContract {
  ERC20 payoutToken;
  address from;
  uint256 initialBalance;

  function PayoutContract(CheckpointToken _token, ERC20 _payoutToken, KYCInterface _KYC, bytes32 name, bytes32 URI, uint256 _type, uint256 _hash, bytes32[] _options) InvestorInteractionContract(_token, _KYC, name, URI, _type, _hash, 0, _options) {
    payoutToken = _payoutToken;
    from = msg.sender;
  }

  function fetchTokens() external {
    require(initialBalance == 0);

    uint256 allowed = payoutToken.allowance(from, address(this));
    payoutToken.transferFrom(from, address(this), allowed);

    initialBalance = payoutToken.balanceOf(address(this));
  }

  function transferTrigger(address from, address to, uint256 amount) internal {
    payoutToken.transfer(from, (amount * initialBalance) / maximumSupply);
    super.transferTrigger(from, to, amount);
  }

}
