// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DIDRegistry {
    struct DIDStruct {
        string did;
        string publicKey;
        bool exists;
    }
    
    mapping(address => DIDStruct) public registry;
    
    // --- SECURITY UPGRADE: ACCESS CONTROL ---
    address public admin;
    mapping(address => bool) public authorizedIssuers;
    
    // Store Merkle Roots: Mapping of (Issuer_DID -> Root_Hash)
    mapping(string => string) public merkleRoots;

    constructor() {
        admin = msg.sender; // The GA (Deployer) is the Admin
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only Admin (GA) can perform this action");
        _;
    }

    modifier onlyAuth() {
        require(authorizedIssuers[msg.sender], "ACCESS DENIED: You are not an authorized Authority.");
        _;
    }

    // GA calls this to authorize RI and LG
    function addAuthority(address _authority) public onlyAdmin {
        authorizedIssuers[_authority] = true;
    }

    function register(string memory _did, string memory _pubKey) public {
        registry[msg.sender] = DIDStruct(_did, _pubKey, true);
    }

    function getPublicKey(address _owner) public view returns (string memory) {
        require(registry[_owner].exists, "DID not registered");
        return registry[_owner].publicKey;
    }

    // --- SECURED FUNCTION ---
    function publishMerkleRoot(string memory _issuerDid, string memory _rootHash) public onlyAuth {
        merkleRoots[_issuerDid] = _rootHash;
    }
    
    function getMerkleRoot(string memory _issuerDid) public view returns (string memory) {
        return merkleRoots[_issuerDid];
    }
}