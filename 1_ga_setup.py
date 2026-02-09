from web3 import Web3
from solcx import compile_source, install_solc, set_solc_version
import json
from key_manager import get_ganache_key
from ssi_utils import w3

def deploy_contract():
    # 1. FORCE COMPILER INSTALLATION & SELECTION
    try:
        print("[Setup] Checking Solidity Compiler...")
        install_solc('0.8.0')
        set_solc_version('0.8.0') 
        print("✅ Solc 0.8.0 ready.")
    except Exception as e:
        print(f"⚠️ Compiler Warning: {e}")

    if not w3.is_connected():
        print("❌ Ganache not running!")
        return

    # Set Default Account (GA - Governance Authority)
    w3.eth.default_account = w3.eth.accounts[0]

    # --- UPDATED SOLIDITY CONTRACT (WITH ACCESS CONTROL) ---
    contract_source_code = '''
    pragma solidity ^0.8.0;

    contract IdentityRegistry {
        struct DIDDoc {
            string did;
            string publicKey;
            bool exists;
        }

        mapping(address => DIDDoc) public registry;
        
        // --- SECURITY UPGRADE: ACCESS CONTROL ---
        address public admin;
        mapping(address => bool) public authorizedIssuers;
        
        // Store Merkle Roots
        mapping(string => string) public merkleRoots;

        // KAC AUDIT LOGGING
        event AuditLog(string indexed verifier, string indexed subject, string action, uint256 timestamp);

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

        // --- FUNCTIONS ---

        // 1. ACCESS CONTROL FUNCTIONS
        function addAuthority(address _authority) public onlyAdmin {
            authorizedIssuers[_authority] = true;
        }

        // 2. REGISTRY FUNCTIONS
        function register(string memory _did, string memory _pubKey) public {
            registry[msg.sender] = DIDDoc(_did, _pubKey, true);
        }

        function getPublicKey(address _owner) public view returns (string memory) {
            require(registry[_owner].exists, "DID not registered");
            return registry[_owner].publicKey;
        }

        // 3. MERKLE ROOT FUNCTIONS (SECURED)
        function publishMerkleRoot(string memory _issuerDid, string memory _root) public onlyAuth {
            merkleRoots[_issuerDid] = _root;
        }

        function getMerkleRoot(string memory _issuerDid) public view returns (string memory) {
            return merkleRoots[_issuerDid];
        }

        // 4. AUDIT LOG FUNCTION
        function logAudit(string memory _verifier, string memory _subject, string memory _action) public {
            emit AuditLog(_verifier, _subject, _action, block.timestamp);
        }
    }
    '''

    print("--- [GA] Compiling Contract with KAC Audit & Access Control ---")
    
    # 2. COMPILE
    compiled_sol = compile_source(
        contract_source_code,
        output_values=['abi', 'bin'],
        solc_version='0.8.0'
    )
    
    contract_id, contract_interface = next(iter(compiled_sol.items()))

    # 3. DEPLOY
    IdentityRegistry = w3.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin'])
    tx_hash = IdentityRegistry.constructor().transact()
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"✅ Contract Deployed at: {tx_receipt.contractAddress}")

    # 4. INSTANTIATE CONTRACT OBJECT (Fixes your error)
    contract = w3.eth.contract(address=tx_receipt.contractAddress, abi=contract_interface['abi'])

    # Save Config
    config = {
        "contract_address": tx_receipt.contractAddress,
        "ga_address": w3.eth.accounts[0],
        "abi": contract_interface['abi']
    }
    with open("system_config.json", "w") as f:
        json.dump(config, f, indent=4)

    print("\n--- [GA] Whitelisting Authorities (Access Control) ---")

    # 1. Get Addresses
    ri_key = get_ganache_key(1)
    lg_key = get_ganache_key(2)
    
    # Convert keys to addresses
    ri_address = w3.eth.account.from_key(ri_key).address
    lg_address = w3.eth.account.from_key(lg_key).address
    ga_address = w3.eth.account.from_key(get_ganache_key(0)).address

    # 2. Authorize RI
    print(f"[GA] Authorizing Research Institute ({ri_address})...")
    contract.functions.addAuthority(ri_address).transact({
        'from': ga_address,
        'gas': 3000000
    })

    # 3. Authorize LG
    print(f"[GA] Authorizing Local Government ({lg_address})...")
    contract.functions.addAuthority(lg_address).transact({
        'from': ga_address,
        'gas': 3000000
    })

    print("✅ Access Control Configured.")

if __name__ == "__main__":
    deploy_contract()