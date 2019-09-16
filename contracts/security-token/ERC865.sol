pragma solidity ^0.4.18;

import "./CheckpointToken.sol";

/* Largely copied from https://github.com/OpenZeppelin/openzeppelin-solidity/pull/741/files */

contract ERC865 is CheckpointToken {
  /** @dev This is used to prevent nonce reuse: */
  mapping(bytes => bool) signatures;

  event TransferPreSigned(address indexed from, address indexed to, address indexed delegate, uint256 amount, uint256 fee);
  event Debug(address from, bytes32 hash);

  /**
    * @notice Submit a presigned transfer
    * @param _signature bytes The signature, issued by the owner.
    * @param _to address The address which you want to transfer to.
    * @param _value uint256 The amount of tokens to be transferred.
    * @param _fee uint256 The amount of tokens paid to msg.sender, by the person who used to own the tokens.
    * @param _nonce uint256 Presigned transaction number
    */
  function transferPreSigned(
    bytes _signature,
    address _to,
    uint256 _value,
    uint256 _fee,
    uint256 _nonce
  )
    public
    returns (bool)
  {
    require(_to != address(0));
    require(signatures[_signature] == false);
    bytes32 hashedTx = transferPreSignedHashing(address(this), _to, _value, _fee, _nonce);
    address from = recover(hashedTx, _signature);
    require(from != address(0));

    _value = verifyTransaction(from, _to, _value);
    _fee = verifyTransaction(from, msg.sender, _fee);

    transferInternal(from, _to, _value);
    transferInternal(from, msg.sender, _fee);

    signatures[_signature] = true;
    TransferPreSigned(from, _to, msg.sender, _value, _fee);
    Transfer(from, _to, _value);
    Transfer(from, msg.sender, _fee);
    return true;
  }

  /**
    * @notice Hash (keccak256) of the payload used by transferPreSigned
    * @param _token address The address of the token.
    * @param _to address The address which you want to transfer to.
    * @param _value uint256 The amount of tokens to be transferred.
    * @param _fee uint256 The amount of tokens paid to msg.sender, by the owner.
    * @param _nonce uint256 Presigned transaction number.
    */
  function transferPreSignedHashing(
    address _token,
    address _to,
    uint256 _value,
    uint256 _fee,
    uint256 _nonce
  )
    public
    pure
    returns (bytes32)
  {
    /* "48664c16": transferPreSignedHashing(address,address,address,uint256,uint256,uint256) */
    return keccak256(bytes4(0x48664c16), _token, _to, _value, _fee, _nonce);
  }

  /**
    * @notice Recover signer address from a message by using his signature.
    *         Signature is delivered as a byte array, hence need for this
    *         implementation.
    * @param hash bytes32 message, the hash is the signed message. What is recovered is the signer address.
    * @param sig bytes signature, the signature is generated using web3.eth.sign()
    */
  function recover(bytes32 hash, bytes sig) public pure returns (address) {
    bytes32 r;
    bytes32 s;
    uint8 v;

    /* Check the signature length */
    if (sig.length != 65) {
      return (address(0));
    }

    /* Divide the signature in r, s and v variables */
    assembly {
      r := mload(add(sig, 32))
      s := mload(add(sig, 64))
      v := byte(0, mload(add(sig, 96)))
    }

    /* Version of signature should be 27 or 28, but 0 and 1 are also possible versions */
    if (v < 27) {
      v += 27;
    }

    /* If the version is correct return the signer address */
    if (v != 27 && v != 28) {
      return (address(0));
    } else {
      return ecrecover(hash, v, r, s);
    }
  }

}
