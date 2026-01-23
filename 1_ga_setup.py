from web3 import Web3
from solcx import compile_source, install_solc, set_solc_version
import json

def deploy_contract():
    # 1. FORCE COMPILER INSTALLATION & SELECTION
    try:
        print("[Setup] Checking Solidity Compiler...")
        install_solc('0.8.0')
        set_solc_version('0.8.0') # <--- Forces the script to use this version
        print("✅ Solc 0.8.0 ready.")
    except Exception as e:
        print(f"⚠️ Compiler Warning: {e}")

    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
    if not w3.is_connected():
        print("❌ Ganache not running!")
        return

    # Set Default Account (GA - Governance Authority)
    w3.eth.default_account = w3.eth.accounts[0]

    # --- SOLIDITY CONTRACT WITH MERKLE & KAC AUDIT ---
    contract_source_code = '''
    pragma solidity ^0.8.0;

    contract IdentityRegistry {
        // Struct to hold Identity Data
        struct DIDDoc {
            string did;
            string pubKey;
            bool exists;
        }

        // 1. REGISTRY STORAGE
        mapping(string => string) public pubKeys;
        mapping(address => string) public addressToDid;
        mapping(string => bool) public didExists;

        // 2. MERKLE ROOT STORAGE (For Revocation/Validity)
        mapping(string => string) public issuerMerkleRoots;

        // 3. KAC AUDIT LOGGING
        event AuditLog(string indexed verifier, string indexed subject, string action, uint256 timestamp);

        // --- FUNCTIONS ---

        function register(string memory _did, string memory _pubKey) public {
            pubKeys[_did] = _pubKey;
            addressToDid[msg.sender] = _did;
            didExists[_did] = true;
        }

        function getPublicKey(string memory _did) public view returns (string memory) {
            require(didExists[_did], "DID not registered");
            return pubKeys[_did];
        }

        // NOVELTY 1: PUBLISH MERKLE ROOT
        function publishMerkleRoot(string memory _did, string memory _root) public {
            issuerMerkleRoots[_did] = _root;
        }

        function getMerkleRoot(string memory _did) public view returns (string memory) {
            return issuerMerkleRoots[_did];
        }

        // NOVELTY 2: KAC AUDIT LOG
        function logAudit(string memory _verifier, string memory _subject, string memory _action) public {
            emit AuditLog(_verifier, _subject, _action, block.timestamp);
        }
    }
    '''

    print("--- [GA] Compiling Contract with KAC Audit & Merkle Logic ---")
    
    # 2. COMPILE WITH EXPLICIT VERSION
    compiled_sol = compile_source(
        contract_source_code,
        output_values=['abi', 'bin'],
        solc_version='0.8.0' # <--- Explicitly tell it to use 0.8.0
    )
    
    contract_id, contract_interface = next(iter(compiled_sol.items()))

    # Deploy
    IdentityRegistry = w3.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin'])
    tx_hash = IdentityRegistry.constructor().transact()
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"✅ Contract Deployed at: {tx_receipt.contractAddress}")

    # Save Config
    config = {
        "contract_address": tx_receipt.contractAddress,
        "ga_address": w3.eth.accounts[0],
        "abi": contract_interface['abi']
    }
    with open("system_config.json", "w") as f:
        json.dump(config, f, indent=4)

if __name__ == "__main__":
    deploy_contract()