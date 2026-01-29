from ssi_utils import SSIEntity, load_json, save_json, w3
from key_manager import get_ganache_key
from merkle_utils import MerkleTree
import json

def run_lg_node():
    # Load Config
    config = load_json("system_config.json")
    
    # Setup Identity (LG is Index 2)
    PKEY_LG = get_ganache_key(2)
    LG = SSIEntity("Local Government", PKEY_LG, config['contract_address'])
    
    print("\n--- [LG] Booting Up & Registering ---")
    LG.register_on_blockchain()

    # --- ISSUING VCs TO OWNERS ---
    print("\n--- [LG] Issuing VCs to 3 Data Owners ---")

    # We simulate 3 Owners (Indices 4, 5, 6)
    owner_keys = [get_ganache_key(4), get_ganache_key(5), get_ganache_key(6)]
    valid_vc_strings = [] # Store VCs for Merkle Tree
    owner_vcs = []

    for i, key in enumerate(owner_keys):
        owner_id = i + 1
        
        # 1. Create Temp Entity to get DID
        temp_owner = SSIEntity(f"Owner_{owner_id}", key)
        temp_owner.register_on_blockchain() # Owner registers their key
        
        # 2. LG Issues VC
        print(f"   📝 Issuing VC to Owner {owner_id} ({temp_owner.did})...")
        vc = LG.issue_credential(
            holder_did=temp_owner.did, 
            holder_address=temp_owner.address, 
            claims={
                "role": "Authorized Hospital", 
                "region": "North_District", 
                "capacity": "Level_1_Trauma"
            }, 
        )
        
        # 3. Save to Disk
        filename = f"vc_owner_{owner_id}.json"
        save_json(filename, vc)
        owner_vcs.append(vc)
        
        # 4. Add to List for Merkle Tree
        vc_str = json.dumps(vc, sort_keys=True)
        valid_vc_strings.append(vc_str)

    # --- NOVELTY: GENERATE OWNER MERKLE TREE ---
    print("\n--- [LG] Building Hospital Trust Tree (HBMT) ---")
    
    # Build Tree from valid VCs
    mt = MerkleTree(valid_vc_strings)
    root = mt.get_root()
    
    print(f"[LG] Generated Hospital Root: {root[:15]}...")
    
    # Publish Root to Blockchain
    print("[LG] 📡 Publishing Root to Blockchain...")
    contract = w3.eth.contract(address=config['contract_address'], abi=config['abi'])
    tx = contract.functions.publishMerkleRoot(LG.did, root).build_transaction({
        'from': LG.address,
        'nonce': w3.eth.get_transaction_count(LG.address),
        'gas': 3000000,
        'gasPrice': w3.to_wei('20', 'gwei')
    })
    signed_tx = w3.eth.account.sign_transaction(tx, LG.account.key)
    w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("[LG] ✅ Hospital Allowlist is Active on Blockchain.")

    # --- ISSUE PROOFS TO OWNERS ---
    # Owners need these proofs to join the Federated Learning rounds
    print("\n--- [LG] Distributing Merkle Proofs to Owners ---")
    for i, vc_str in enumerate(valid_vc_strings):
        proof = mt.get_proof(vc_str)
        filename = f"merkle_proof_owner_{i+1}.json"
        save_json(filename, proof)
        print(f"   🎟️  Proof saved for Owner {i+1}")

if __name__ == "__main__":
    run_lg_node()