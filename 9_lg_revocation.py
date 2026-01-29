import json
from ssi_utils import SSIEntity, load_json, save_json, w3
from merkle_utils import MerkleTree
from key_manager import get_ganache_key

def revoke_hospital():
    print("\n" + "="*60)
    print("      🏥  LOCAL GOV SECURITY CONSOLE: HOSPITAL BAN      ")
    print("="*60)

    # 1. SETUP
    try:
        config = load_json("system_config.json")
        contract = w3.eth.contract(address=config['contract_address'], abi=config['abi'])
    except Exception as e:
        print(f"❌ Error loading system: {e}")
        return

    # Authenticate as Local Gov (Index 2)
    LG = SSIEntity("Local Government", get_ganache_key(2), config['contract_address'])

    # 2. LOAD CURRENT HOSPITALS
    hospitals = {}
    for i in range(1, 4): # Owners 1, 2, 3
        try:
            vc = load_json(f"vc_owner_{i}.json")
            hospitals[str(i)] = {
                "name": f"City Hospital {i}", 
                "did": vc['payload']['credentialSubject']['id'],
                "data": json.dumps(vc, sort_keys=True)
            }
        except:
            pass

    # 3. INTERACTIVE MENU
    print(f"\n[Status] Managing {len(hospitals)} Authorized Hospitals.")
    print("Which Hospital is compromised/poisoning the model?\n")
    
    for key, info in hospitals.items():
        print(f"   [{key}] {info['name']} ({info['did'][:18]}...)")
    
    choice = input("\n👉 Select Hospital ID to BAN: ").strip()

    if choice not in hospitals:
        print("❌ Invalid selection.")
        return

    banned_hospital = hospitals[choice]
    print(f"\n[Action] ⛔ REVOKING LICENSE FOR: {banned_hospital['name']}...")

    # 4. REBUILD TREE EXCLUDING THE BAD HOSPITAL
    new_valid_list = []
    valid_indices = [] # Keep track of who is still valid

    for key, info in hospitals.items():
        if key != choice:
            new_valid_list.append(info['data'])
            valid_indices.append(key)
            print(f"   ✅ Retaining: {info['name']}")
        else:
            print(f"   ❌ Dropping:  {info['name']}")

    # Generate New Root
    if not new_valid_list:
        print("❌ Error: Cannot ban everyone. Tree must have at least 1 leaf.")
        return

    mt = MerkleTree(new_valid_list)
    new_root = mt.get_root()
    
    print(f"\n[Result] New Hospital Root: {new_root[:15]}...")

    # 5. UPDATE BLOCKCHAIN
    print("[Blockchain] 📡 Updating Ledger...")
    try:
        tx = contract.functions.publishMerkleRoot(LG.did, new_root).build_transaction({
            'from': LG.address,
            'nonce': w3.eth.get_transaction_count(LG.address),
            'gas': 3000000,
            'gasPrice': w3.to_wei('20', 'gwei')
        })
        signed_tx = w3.eth.account.sign_transaction(tx, LG.account.key)
        w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"[Success] ✅ Root updated on Blockchain.")
        
        # --- NEW STEP: ISSUE FRESH PROOFS TO SURVIVORS ---
        print("\n[Maintenance] 🔄 Issuing NEW Merkle Proofs to valid hospitals...")
        for i, vc_str in enumerate(new_valid_list):
            proof = mt.get_proof(vc_str)
            owner_id = valid_indices[i] # Get the original ID (e.g., "1" or "3")
            
            # Overwrite the old proof file
            filename = f"merkle_proof_owner_{owner_id}.json"
            save_json(filename, proof)
            print(f"   🎟️  Updated proof for Owner {owner_id}")

        print(f"\n[Complete] {banned_hospital['name']} is now mathematically locked out.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    revoke_hospital()