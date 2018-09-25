pragma solidity ^0.4.18;

import "./BogusTAPASAnnouncement.sol";
import "./MockKYC.sol";
import "../CheckpointToken.sol";
import "zeppelin/contracts/token/ERC20/StandardToken.sol";

contract InvestorInteractionContract is BogusTAPASAnnouncement, StandardToken {
  uint256 public blockNumber;
  CheckpointToken token;
  mapping(address => bool) public balanceImported;
  uint256 maximumSupply;
  MockKYC KYC;

  function InvestorInteractionContract(CheckpointToken _token, MockKYC _KYC, uint256 _blockNumber) public {
    token = _token;
    blockNumber = _blockNumber;
    KYC = _KYC;

    maximumSupply = token.totalSupplyAt(blockNumber);
  }

  function importInvestor(address investor) public {
    // This will be embeded to the final version's token code
    // Anyone can invoke this for failsafe reasons

    require(balanceImported[investor] == false);

    uint256 balance = token.balanceAt(investor, blockNumber);
    totalSupply_ += balance;
    balances[investor] += balance;

    balanceImported[investor] = true;
    Transfer(address(0), investor, balance);
  }

  function transfer(address _to, uint256 _value) public returns (bool) {
    if (balanceImported[msg.sender] == false) {
      importInvestor(msg.sender);
    }

    require(KYC.isWhitelisted(msg.sender));

    // Doing this as msg.sender:
    return super.transfer(_to, _value);
  }
}
