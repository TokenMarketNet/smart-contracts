pragma solidity ^0.4.18;

import "./InvestorInteractionContract.sol";
import "../KYCInterface.sol";

contract VotingContract is InvestorInteractionContract {

  function VotingContract(CheckpointToken _token, KYCInterface _KYC, bytes32 name, bytes32 URI, uint256 _type, uint256 _hash, bytes32[] _options) InvestorInteractionContract(_token, _KYC, name, URI, _type, _hash, 0, _options) {

  }
}
