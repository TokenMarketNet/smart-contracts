/**
 * This smart contract code is Copyright 2017 TokenMarket Ltd. For more information see https://tokenmarket.net
 * Author: Ville Sundell <ville at tokenmarket.net>
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 */

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
  event UpdatedTokenInformation(string newName, string newSymbol);

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

  /**
  * Whitelisted can update token information here.
  *
  * It is often useful to conceal the actual token association, until
  * the token operations, like central issuance or reissuance have been completed.
  *
  * This function allows the token owner to rename the token after the operations
  * have been completed and then point the audience to use the token contract.
  */
  function setTokenInformation(string _name, string _symbol) external onlyWhitelisted {
    name = _name;
    symbol = _symbol;

    UpdatedTokenInformation(name, symbol);
  }
}
