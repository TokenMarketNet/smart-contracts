pragma solidity ^0.4.18;

import "./BogusAnnouncement.sol";
import "../KYCInterface.sol";
import "../CheckpointToken.sol";
import "zeppelin/contracts/token/ERC20/StandardToken.sol";

contract InvestorInteractionContract is BogusAnnouncement, StandardToken {
  uint256 public blockNumber;
  CheckpointToken public token;
  mapping(address => bool) public balanceImported;

  uint256 maximumSupply;
  KYCInterface KYC;

  mapping(address => bytes32) public options;
  mapping(address => mapping(address => uint256)) public used;
  uint256 public optionsTotal;
  uint256 public maximumSupply;

  event OptionAdded(address option, bytes32 description);
  event IICCreated(address token, address KYC, uint256 blockNumber, uint256 maximumSupply);

  function InvestorInteractionContract(CheckpointToken _token, KYCInterface _KYC, bytes32 name, bytes32 URI, uint256 _type, uint256 _hash, uint256 _blockNumber, bytes32[] _options) BogusAnnouncement(name, URI, _type, _hash) public {
    token = _token;
    if (_blockNumber > 0) {
      blockNumber = _blockNumber;
    } else {
      blockNumber = block.number;
    }
    KYC = _KYC;

    for(uint i=0; i<_options.length; i++) {
      address optionAddress = address(100 + i);
      options[optionAddress] = _options[i];

      OptionAdded(optionAddress, _options[i]);
    }

    maximumSupply = token.totalSupplyAt(blockNumber);

    IICCreated(_token, _KYC, _blockNumber, maximumSupply);
  }

  function importInvestor(address investor) public {
    // Anyone can invoke this for failsafe reasons

    require(balanceImported[investor] == false);

    uint256 balance = token.balanceAt(investor, blockNumber);
    totalSupply_ += balance;
    balances[investor] += balance;

    balanceImported[investor] = true;
    Transfer(address(0), investor, balance);
  }

  function transferInvestorTokens(address to, uint256 amount) {
    transfer(to, amount);
  }


  function transferTrigger(address from, address to, uint256 amount) internal {
    used[to][from] += amount;
  }

  function transfer(address _to, uint256 _value) public returns (bool) {
    if (balanceImported[msg.sender] == false) {
      importInvestor(msg.sender);
    }

    if (options[_to] != 0) {
      require(KYC.isWhitelisted(msg.sender));
      transferTrigger(msg.sender, _to, _value);
    }

    // Doing this as msg.sender:
    return super.transfer(_to, _value);
  }
}
