

/**
 * Test address hash behavior with left and right padded zeroes.
 */
contract TestSolidityAddressHash {

  address public leftPad = 0x00b5557397B157a17fb1AbCa97a38e4646BEDb88;
  address public rightPad = 0x88b5557397B157a17fb1AbCa97a38e4646BEDb00;

  function getHashLeftPad() public constant returns (bytes32) {
    bytes32 hash = sha256(leftPad);
    return hash;
  }

  function getHashRightPad() public constant returns (bytes32) {
    bytes32 hash = sha256(rightPad);
    return hash;
  }

}
