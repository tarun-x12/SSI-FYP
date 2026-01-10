// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DIDRegistry {
    struct DIDStruct {
        string did;
        string publicKey;
        bool exists;
    }
    mapping(address => DIDStruct) public registry;

    function register(string memory _did, string memory _pubKey) public {
        registry[msg.sender] = DIDStruct(_did, _pubKey, true);
    }

    function getPublicKey(address _owner) public view returns (string memory) {
        require(registry[_owner].exists, "DID not registered");
        return registry[_owner].publicKey;
    }
}