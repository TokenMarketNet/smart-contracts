import "../BytesDeserializer.sol";

contract TestBytesDeserializer {

    using BytesDeserializer for bytes;

    function getUint256(bytes b, uint offset) public constant returns (uint256) {
      return uint256(b.slice32(offset));
    }

    function getUint128(bytes b, uint offset) public constant returns (uint256) {
      return uint128(b.slice16(offset));
    }

    function getUint32(bytes b, uint offset) public constant returns (uint256) {
      return uint32(b.slice4(offset));
    }

    function getUint16(bytes b, uint offset) public constant returns (uint256) {
      return uint16(b.slice2(offset));
    }

    function getBytes32(bytes b, uint offset) public constant returns (bytes32) {
      return b.slice32(offset);
    }

    function getAddress(bytes b, uint offset) public constant returns (address) {
      return b.sliceAddress(offset);
    }

}
