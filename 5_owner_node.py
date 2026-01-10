import sys
import os
import torch
import torch.nn as nn
import pandas as pd
import time
from ssi_utils import SSIEntity, load_json
from key_manager import get_ganache_key
from fl_utils import HybridDL, preprocess_data, apply_ldp
from cloud_client import CloudAgentClient

# Global queue for incoming requests
incoming_requests = []

def on_request_received(msg):
    """Callback: Triggered when M1 (Connection Request) arrives"""
    if msg.get('type') == 'M1':
        print(f"\n[Cloud] 📩 Received Request (M1) from {msg['from']}")
        incoming_requests.append(msg)

def run_owner_node(owner_index):
    # --- SETUP ---
    config = load_json("system_config.json")
    ganache_index = owner_index + 3
    owner_name = f"Owner_{owner_index}"
    dataset_file = f"dataset_owner_{owner_index}.csv"
    vc_filename = f"vc_owner_{owner_index}.json"

    print(f"--- Booting Up {owner_name} (Device {owner_index}) ---")

    # 1. Load Identity
    pkey = get_ganache_key(ganache_index)
    Owner = SSIEntity(owner_name, pkey, config['contract_address'])

    # ---------------------------------------------------------
    # 🔥 CRITICAL FIX: ALWAYS REGISTER ON BLOCKCHAIN ON STARTUP
    # ---------------------------------------------------------
    print(f"[{owner_name}] Ensuring Blockchain Registration...")
    try:
        # Force registration so the Analyst can verify us later
        Owner.register_on_blockchain()
    except Exception as e:
        print(f"⚠️ Registration warning: {e}")
    # ---------------------------------------------------------
    
    # 2. Load VC
    if not os.path.exists(vc_filename):
        print(f"❌ Error: {vc_filename} missing. Run 3_lg_node.py first.")
        return
    my_vc = load_json(vc_filename)

    # 3. CONNECT TO CLOUD
    cloud = CloudAgentClient(Owner.did, on_request_received)
    cloud.connect()

    print(f"[{owner_name}] Listening for Training Requests...")

    # --- MAIN LOOP ---
    while True:
        if len(incoming_requests) > 0:
            # Process the oldest request
            msg = incoming_requests.pop(0)
            req = msg['payload']
            sender_did = msg['from']

            print(f"[{owner_name}] Verifying Analyst {sender_did}...")
            
            # --- STEP A: SECURITY CHECK ---
            try:
                is_zk = Owner.verify_zk_proof(req['sender_address'], req['challenge_context'], req['proof_nizkp'])
                is_vc = Owner.verify_vc_issuer(req['vc'])

                if is_zk and is_vc:
                    print(f"[{owner_name}] ✅ Trusted Analyst. Starting Training...")
                    
                    # --- STEP B: LOCAL TRAINING ---
                    try:
                        raw_df = pd.read_csv(dataset_file)
                        X_proc, y_proc = preprocess_data(raw_df)
                        
                        # Privacy: Add Noise
                        X_priv = apply_ldp(X_proc, epsilon=2.0)
                        
                        # Convert to Tensors
                        X_tensor = torch.FloatTensor(X_priv)
                        y_tensor = torch.FloatTensor(y_proc).unsqueeze(1)
                        
                        # Initialize Model
                        model = HybridDL(X_priv.shape[1])
                        criterion = nn.MSELoss()
                        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
                        
                        # Train
                        model.train()
                        for epoch in range(5):
                            optimizer.zero_grad()
                            output = model(X_tensor)
                            loss = criterion(output, y_tensor)
                            loss.backward()
                            optimizer.step()
                        
                        print(f"[{owner_name}] Training Done (Loss: {loss.item():.4f}). Sending Results...")

                        # --- STEP C: SEND REPLY (M2) ---
                        local_weights = model.state_dict()
                        # Serialize (Tensor -> List)
                        weights_json = {k: v.tolist() for k, v in local_weights.items()}
                        
                        # Generate Proof of Acceptance
                        reply_ctx = f"FL_ACCEPT_{int(time.time())}"
                        proof_pr_o = Owner.generate_zk_proof(reply_ctx)

                        reply_payload = {
                            "sender_did": Owner.did,
                            "sender_address": Owner.address,
                            "vc": my_vc,
                            "proof_nizkp": proof_pr_o,
                            "challenge_context": reply_ctx,
                            "weights": weights_json,
                            "meta": {"data_rows": len(X_priv)}
                        }

                        cloud.send(sender_did, "M2", reply_payload)
                        print(f"[{owner_name}] 📤 Sent M2 Reply to Analyst.")
                        
                    except Exception as e:
                        print(f"❌ Training Error: {e}")
                else:
                    print(f"[{owner_name}] ❌ Security Failed. Ignoring Request.")
            except Exception as e:
                print(f"[{owner_name}] ❌ Verification Error: {e}")
        
        # Idle wait
        time.sleep(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python 5_owner_node.py <OWNER_INDEX>")
    else:
        idx = int(sys.argv[1])
        run_owner_node(idx)