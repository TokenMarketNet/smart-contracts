pragma solidity ^0.4.18;

import "./CrowdsaleToken.sol";
import "./CheckpointToken.sol";
import "./Recoverable.sol";
import "zeppelin/contracts/ownership/Whitelist.sol";

/// @dev TAPAS proposal interface
interface TAPASProposal {
  function proposalName() public view returns (bytes32);
  function proposalURI() public view returns (bytes32);
  function proposalType() public view returns (uint256);
}

contract TAPASToken is CheckpointToken, Whitelist, Recoverable {

  // TAPAS specific
  event Issued(address indexed to, uint256 value);
  event Burned(address indexed burner, uint256 value);
  event Announced(address indexed proposal, uint256 indexed proposalType, bytes32 indexed proposalName, bytes32 proposalURI);

  address[] public proposals;

  function TAPASToken(string _name, string _symbol) CheckpointToken(_name, _symbol, 18) public {

  }

  function announce(TAPASProposal proposal) external onlyWhitelisted {
    proposals.push(proposal);
    Announced(proposal, proposal.proposalType(), proposal.proposalName(), proposal.proposalURI());
  }

  function forceTransfer(address from, address to, uint256 value) external onlyWhitelisted {
    transferInternal(from, to, value);
  }

  function issueTokens(uint256 value) external onlyWhitelisted {
    address issuer = msg.sender;
    uint256 zeroBalance = balanceOf(address(0)); /// TODO: Rename!
    uint256 totalSupplyNow = totalSupply();

    setCheckpoint(tokenBalances[address(0)], zeroBalance.add(value));
    transferInternal(address(0), issuer, value);
    setCheckpoint(tokensTotal, totalSupplyNow.add(value));

    Issued(issuer, value);
  }

  function burnTokens(uint256 value) external onlyWhitelisted {
    // Burning only tokens sent to this contract, this way we avoid causing problems to other shareholders by accident
    address burner = address(this);
    uint256 burnerBalance = balanceOf(burner);
    uint256 totalSupplyNow = totalSupply();

    transferInternal(burner, address(0), value);
    setCheckpoint(tokenBalances[address(0)], burnerBalance.sub(value));
    setCheckpoint(tokensTotal, totalSupplyNow.sub(value));

    Burned(burner, value);
  }

}
