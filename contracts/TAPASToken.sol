/**
 * This smart contract code is Copyright 2018 TokenMarket Ltd. For more information see https://tokenmarket.net
 * Licensed under the Apache License, version 2.0: https://github.com/TokenMarketNet/ico/blob/master/LICENSE.txt
 * NatSpec is used intentionally to cover also other than public functions
 * Solidity 0.4.18 is intentionally used: it's stable, and our framework is
 * based on that.
 */

pragma solidity ^0.4.18;

import "./CrowdsaleToken.sol";
import "./CheckpointToken.sol";
import "./Recoverable.sol";
import "zeppelin/contracts/math/SafeMath.sol";
import "zeppelin/contracts/ownership/Whitelist.sol";

/**
 * @dev Interface for general TAPAS announcements.
 *
 * TAPASAnnouncements can be for instance for dividend sharing, voting, or
 * just for general announcements.
 */
interface TAPASAnnouncement {
  function announcementName() public view returns (bytes32);
  function announcementURI() public view returns (bytes32);
  function announcementType() public view returns (uint256);
  function announcementHash() public view returns (uint256);
}

/**
 * @author TokenMarket /  Ville Sundell <ville at tokenmarket.net>
 */
contract TAPASToken is CheckpointToken, Whitelist, Recoverable {
  using SafeMath for uint256; // We use only uint256 for safety reasons (no boxing)

  /** TAPAS specific events **/
  event Issued(address indexed to, uint256 value);
  event Burned(address indexed burner, uint256 value);
  event Forced(address indexed from, address indexed to, uint256 value);
  event Announced(address indexed announcement, uint256 indexed announcementType, bytes32 indexed announcementName, bytes32 announcementURI, uint256 announcementHash);
  event UpdatedTokenInformation(string newName, string newSymbol);

  address[] public announcements;

  /**
   * @dev Contructor to create TAPASToken, and subsequent CheckpointToken.
   *
   * CheckpointToken will be created with hardcoded 18 decimals.
   *
   * @param _name Initial name of the token
   * @param _symbol Initial symbol of the token
   */
  function TAPASToken(string _name, string _symbol) CheckpointToken(_name, _symbol, 18) public {

  }

  /**
   * @dev Function to announce TAPASAnnouncements.
   *
   * TAPASAnnouncements can be for instance for dividend sharing, voting, or
   * just for general announcements.
   *
   * Instead of storing the announcement details, we just broadcast them as an
   * event, and store only the address.
   *
   * @param announcement Address of TAPASAnnouncement
   */
  function announce(TAPASAnnouncement announcement) external onlyWhitelisted {
    announcements.push(announcement);
    Announced(address(announcement), announcement.announcementType(), announcement.announcementName(), announcement.announcementURI(), announcement.announcementHash());
  }

  /**
   * @dev Function to forcefully transfer tokens from A to B by board decission
   *
   * This must be implemented carefully, since this is a very critical part
   * to ensure investor safety.
   *
   * This is intended to be called by the BAC (The Board), hence the whitelisting.
   *
   * @param from Address of the account to confisticate the tokens from
   * @param to Address to deposit the confisticated token to
   * @param value amount of tokens to be confisticated
   */
  function forceTransfer(address from, address to, uint256 value) external onlyWhitelisted {
    transferInternal(from, to, value);

    Forced(from, to, value);
  }

  /**
   * @dev Issue new tokens to the board by a board decission
   *
   * Issue new tokens. This is intended to be called by the BAC (The Board),
   * hence the whitelisting.
   *
   * @param value Token amount to issue
   */
  function issueTokens(uint256 value) external onlyWhitelisted {
    address issuer = msg.sender;
    uint256 blackHoleBalance = balanceOf(address(0));
    uint256 totalSupplyNow = totalSupply();

    setCheckpoint(tokenBalances[address(0)], blackHoleBalance.add(value));
    transferInternal(address(0), issuer, value);
    setCheckpoint(tokensTotal, totalSupplyNow.add(value));

    Issued(issuer, value);
  }

  /**
   * @dev Burn tokens from contract's own balance by a board decission
   *
   * Burn tokens from contract's own balance to prevent accidental burnings.
   * This is intended to be called by the BAC (The Board), hence the whitelisting.
   *
   * @param value Token amount to burn from this contract's balance
   */
  function burnTokens(uint256 value) external onlyWhitelisted {
    address burner = address(this);
    uint256 burnerBalance = balanceOf(burner);
    uint256 totalSupplyNow = totalSupply();

    transferInternal(burner, address(0), value);
    setCheckpoint(tokenBalances[address(0)], burnerBalance.sub(value));
    setCheckpoint(tokensTotal, totalSupplyNow.sub(value));

    Burned(burner, value);
  }

  /**
  * @dev Whitelisted users (The Board, BAC) can update token information here.
  *
  * It is often useful to conceal the actual token association, until
  * the token operations, like central issuance or reissuance have been completed.
  *
  * This function allows the token owner to rename the token after the operations
  * have been completed and then point the audience to use the token contract.
  *
  * @param _name New name of the token
  * @param _symbol New symbol of the token
  */
  function setTokenInformation(string _name, string _symbol) external onlyWhitelisted {
    name = _name;
    symbol = _symbol;

    UpdatedTokenInformation(name, symbol);
  }
}
