pragma solidity ^0.4.18;

contract BogusTAPASAnnouncement {
  bytes32 public announcementName;
  bytes32 public announcementURI;
  uint256 public announcementType;

  function BogusTAPASAnnouncement(bytes32 _announcementName, bytes32 _announcementURI, uint256 _announcementType) public {
    announcementName = _announcementName;
    announcementURI = _announcementURI;
    announcementType = _announcementType;
  }
}
