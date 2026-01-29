import time
import glob
import torch
import json
import sys
from ssi_utils import SSIEntity, load_json, w3  
from key_manager import get_ganache_key
from cloud_client import CloudAgentClient
from merkle_utils import verify_merkle_proof

# Global list to store incoming model updates
incoming_replies = []

def on_reply_received(msg):
    """Callback: Triggered when M2 (Model Update) arrives from Cloud"""
    if msg.get('type') == 'M2':
        sender = msg['from']
        print(f"\n   📩 [Cloud] Received M2 (Model Update) from {sender}")
        incoming_replies.append(msg['payload'])

def run_persistent_analyst():
    # --- SETUP IDENTITY ---
    try:
        config = load_json("system_config.json")
    except:
        print("❌ Error: system_config.json not found. Run 1_ga_setup.py first.")
        return

    PKEY_A = get_ganache_key(3) # Analyst is Index 3
    Analyst = SSIEntity("Data Analyst", PKEY_A, config['contract_address'])
    
    print(f"[{Analyst.name}] Ensuring Blockchain Registration...")
    try:
        Analyst.register_on_blockchain()
    except Exception as e:
        print(f"⚠️ Registration warning: {e}")
    
    # 1. CONNECT TO CLOUD
    cloud = CloudAgentClient(Analyst.did, on_reply_received)
    cloud.connect()

    # --- PHASE 1: DISCOVERY & BROADCAST (M1) ---
    print("\n--- [Analyst] Phase 1: Discovering & Contacting Owners ---")
    
    owner_files = glob.glob("vc_owner_*.json")
    if len(owner_files) == 0:
        print("❌ No Owner VCs found. Please run 3_lg_node.py.")
        return

    print(f"✅ Discovered {len(owner_files)} authorized Owners.")

    challenge_msg = f"FL_SESSION_{int(time.time())}"
    proof_pr_a = Analyst.generate_zk_proof(challenge_msg)
    
    # Load Analyst VC
    try:
        vc_analyst = load_json("vc_analyst.json")
    except FileNotFoundError:
        print("❌ Error: 'vc_analyst.json' missing. Run 2_ri_node.py first.")
        return

    # Load Merkle Proof
    merkle_proof = None
    try:
        merkle_proof = load_json("merkle_proof_analyst.json")
        print("✅ Loaded Merkle Proof for validation.")
    except FileNotFoundError:
        print("⚠️ Warning: Merkle Proof not found. Owner validation might fail.")

    payload = {
        "sender_did": Analyst.did,
        "sender_address": Analyst.address,
        "vc": vc_analyst,
        "proof_nizkp": proof_pr_a,
        "challenge_context": challenge_msg,
        "merkle_proof": merkle_proof
    }
    
    sent_count = 0
    for filename in owner_files:
        try:
            owner_data = load_json(filename)
            vc_payload = owner_data.get('payload', {})
            if 'credentialSubject' in vc_payload:
                target_did = vc_payload['credentialSubject']['id']
            elif 'holder' in vc_payload:
                target_did = vc_payload['holder']
            else:
                raise ValueError(f"Could not find DID in {filename}")

            print(f"   📡 Sending Request to {target_did}...")
            cloud.send(target_did, "M1", payload)
            sent_count += 1
        except Exception as e:
            print(f"   ⚠️ Failed to load {filename}: {e}")

    if sent_count == 0:
        print("❌ No requests sent. Exiting.")
        return

    print(f"\n--- [Analyst] Phase 2: Waiting for {sent_count} Replies ---")
    
    start_time = time.time()
    TIMEOUT_SECONDS = 150  # Stop waiting after 60 seconds
    
    while True:
        count = len(incoming_replies)
        elapsed = int(time.time() - start_time)
        remaining = TIMEOUT_SECONDS - elapsed
        
        print(f"\r   > Status: Received {count}/{sent_count} | Timeout in {remaining}s...", end="")
        
        # Condition 1: All received
        if count >= sent_count:
            print("\n   ✅ All targeted owners have replied! Starting Aggregation...")
            break
        
        # Condition 2: Timeout reached (Partial Aggregation)
        if elapsed >= TIMEOUT_SECONDS:
            print(f"\n   ⚠️ Timeout Reached! Proceeding with {count}/{sent_count} updates.")
            if count == 0:
                print("   ❌ No updates received. Aborting.")
                return
            break
            
        time.sleep(2)

    # --- PHASE 3: AGGREGATION ---
    print("\n--- [Analyst] Phase 3: Global Aggregation (FedAvg) ---")
    
    global_weights = None
    total_samples = 0
    valid_updates = 0
    for reply in incoming_replies:
        sender_did = reply['sender_did']
        
        try:
            # 1. Standard Checks (ZK + VC)
            is_zk = Analyst.verify_zk_proof(reply['sender_address'], reply['challenge_context'], reply['proof_nizkp'])
            is_vc = Analyst.verify_vc_issuer(reply['vc'])
            
            # 2. Merkle Check (LG Root)
            is_merkle_valid = False
            try:
                vc_string = json.dumps(reply['vc'], sort_keys=True)
                proof = reply.get('merkle_proof')
                issuer_did = reply['vc']['payload']['issuer'] 
                contract = w3.eth.contract(address=config['contract_address'], abi=config['abi'])
                blockchain_root = contract.functions.getMerkleRoot(issuer_did).call()
                
                if blockchain_root and proof:
                    is_merkle_valid = verify_merkle_proof(vc_string, proof, blockchain_root)
                elif not blockchain_root:
                    print(f"   ⚠️ No Root found for issuer {issuer_did}")
            except Exception as e:
                print(f"   ⚠️ Merkle Check Error: {e}")

            # 3. Aggregation Logic
            if is_zk and is_vc and is_merkle_valid:
                print(f"   ✅ Verified Model from {sender_did} (Identity + Merkle)")
                
                # --- THIS WAS LIKELY MISSING BEFORE ---
                # Convert list back to tensor
                local_weights = {k: torch.tensor(v) for k, v in reply['weights'].items()}
                num_samples = reply['meta']['data_rows']
                
                if global_weights is None:
                    # Initialize global weights with the first valid model
                    global_weights = {k: v * num_samples for k, v in local_weights.items()}
                else:
                    # Aggregate (Weighted Sum)
                    for k in global_weights.keys():
                        global_weights[k] += local_weights[k] * num_samples
                
                total_samples += num_samples
                valid_updates += 1
                # --------------------------------------
                
            else:
                print(f"   ❌ Rejected update from {sender_did} (Security Check Failed)")

        except Exception as e:
            print(f"   ❌ Error verifying {sender_did}: {e}")
    
    # Finalize
    if global_weights and total_samples > 0:
        # Calculate Average
        for k in global_weights.keys():
            global_weights[k] = global_weights[k] / total_samples
            
        torch.save(global_weights, "global_model_final.pth")
        print(f"\n✅ [SUCCESS] Global Model Aggregated from {valid_updates} Owners.")
        print("💾 Saved to: global_model_final.pth")
    else:
        print("❌ Aggregation Failed (No valid models accumulated).")

if __name__ == "__main__":
    run_persistent_analyst()