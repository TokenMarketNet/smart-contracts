import "../BytesDeserializer.sol";

contract TestBytesDeserializer {

    using BytesDeserializer for bytes;

    function getUint256(bytes b, uint offset) public constant returns (uint256) {
      return uint256(b.slice32(offset));
    }

    function getBytes32(bytes b, uint offset) public constant returns (bytes32) {
      return b.slice32(offset);
    }

}
