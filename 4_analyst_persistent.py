import time
import glob
import torch
import json
from ssi_utils import SSIEntity, load_json
from key_manager import get_ganache_key
from cloud_client import CloudAgentClient

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
    config = load_json("system_config.json")
    PKEY_A = get_ganache_key(3) # Analyst is Index 3
    Analyst = SSIEntity("Data Analyst", PKEY_A, config['contract_address'])
    
    # ---------------------------------------------------------
    # 🔥 CRITICAL FIX: ALWAYS REGISTER ON BLOCKCHAIN ON STARTUP
    # ---------------------------------------------------------
    print(f"[{Analyst.name}] Ensuring Blockchain Registration...")
    try:
        # We call this explicitly to ensure the Smart Contract has our Public Key
        Analyst.register_on_blockchain()
    except Exception as e:
        print(f"⚠️ Registration warning (might already be registered): {e}")
    # ---------------------------------------------------------
    
    # 1. CONNECT TO CLOUD
    cloud = CloudAgentClient(Analyst.did, on_reply_received)
    cloud.connect()

    # --- PHASE 1: DISCOVERY & BROADCAST (M1) ---
    print("\n--- [Analyst] Phase 1: Discovering & Contacting Owners ---")
    
    # Discovery: Find all owner files in the folder
    owner_files = glob.glob("vc_owner_*.json")
    if len(owner_files) == 0:
        print("❌ No Owner VCs found. Please run 3_lg_node.py.")
        return

    print(f"✅ Discovered {len(owner_files)} authorized Owners.")

    challenge_msg = f"FL_SESSION_{int(time.time())}"
    proof_pr_a = Analyst.generate_zk_proof(challenge_msg)
    
    # Load VC (Created by 2_ri_node.py)
    try:
        vc_analyst = load_json("vc_analyst.json")
    except FileNotFoundError:
        print("❌ Error: 'vc_analyst.json' missing. Run 2_ri_node.py first.")
        return

    payload = {
        "sender_did": Analyst.did,
        "sender_address": Analyst.address,
        "vc": vc_analyst,
        "proof_nizkp": proof_pr_a,
        "challenge_context": challenge_msg
    }
    
    sent_count = 0
    for filename in owner_files:
        try:
            owner_data = load_json(filename)
            target_did = owner_data['payload']['holder']
            
            print(f"   📡 Sending Request to {target_did}...")
            cloud.send(target_did, "M1", payload)
            sent_count += 1
        except Exception as e:
            print(f"   ⚠️ Failed to load {filename}: {e}")

    if sent_count == 0:
        print("❌ No requests sent. Exiting.")
        return

    # --- PHASE 2: LISTENING LOOP ---
    print(f"\n--- [Analyst] Phase 2: Waiting for {sent_count} Replies ---")
    
    # Wait loop
    while True:
        count = len(incoming_replies)
        print(f"\r   > Status: Received {count}/{sent_count} model updates...", end="")
        
        if count >= sent_count:
            print("\n   ✅ All targeted owners have replied! Starting Aggregation...")
            break
            
        time.sleep(2)

    # --- PHASE 3: AGGREGATION ---
    print("\n--- [Analyst] Phase 3: Global Aggregation (FedAvg) ---")
    
    global_weights = None
    total_samples = 0
    valid_updates = 0
    
    for reply in incoming_replies:
        sender_did = reply['sender_did']
        
        # Security Check wrapped in try/except to prevent crashes
        try:
            is_zk = Analyst.verify_zk_proof(reply['sender_address'], reply['challenge_context'], reply['proof_nizkp'])
            is_vc = Analyst.verify_vc_issuer(reply['vc'])
            
            if is_zk and is_vc:
                print(f"   ✅ Verified Model from {sender_did}")
                
                # Convert list back to tensor
                local_weights = {k: torch.tensor(v) for k, v in reply['weights'].items()}
                num_samples = reply['meta']['data_rows']
                
                if global_weights is None:
                    global_weights = {k: v * num_samples for k, v in local_weights.items()}
                else:
                    for k in global_weights.keys():
                        global_weights[k] += local_weights[k] * num_samples
                
                total_samples += num_samples
                valid_updates += 1
            else:
                print(f"   ❌ Rejected update from {sender_did} (Security Check Failed)")
        except Exception as e:
            print(f"   ❌ Error verifying {sender_did}: {e}")
    
    # Finalize
    if global_weights and total_samples > 0:
        for k in global_weights.keys():
            global_weights[k] = global_weights[k] / total_samples
            
        torch.save(global_weights, "global_model_final.pth")
        print(f"\n✅ [SUCCESS] Global Model Aggregated from {valid_updates} Owners.")
        print("💾 Saved to: global_model_final.pth")
    else:
        print("❌ Aggregation Failed.")

if __name__ == "__main__":
    run_persistent_analyst()