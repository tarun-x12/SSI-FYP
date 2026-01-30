import sys
import os
import torch
import torch.nn as nn
import pandas as pd
import time
import json
from ssi_utils import SSIEntity, load_json, get_contract, w3 
from key_manager import get_ganache_key
from fl_utils import HybridDL, preprocess_data, apply_ldp
from cloud_client import CloudAgentClient
from merkle_utils import verify_merkle_proof

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

    print(f"[{owner_name}] Ensuring Blockchain Registration...")
    try:
        Owner.register_on_blockchain()
    except Exception as e:
        print(f"⚠️ Registration warning: {e}")
    
    # 2. Load VC
    if not os.path.exists(vc_filename):
        print(f"❌ Error: {vc_filename} missing. Run 3_lg_node.py first.")
        return
    my_vc = load_json(vc_filename)

    # 3. CONNECT TO CLOUD
    cloud = CloudAgentClient(Owner.did, on_request_received)
    cloud.connect()

    print(f"[{owner_name}] Listening for Training Requests...")
    contract = get_contract(config['contract_address']) # Load Contract Instance

    # --- MAIN LOOP ---
    while True:
        if len(incoming_requests) > 0:
            msg = incoming_requests.pop(0)
            req = msg['payload']
            sender_did = msg['from']

            print(f"[{owner_name}] Verifying Analyst {sender_did}...")
            
            try:
                # --- STEP A: STANDARD SECURITY CHECK ---
                is_zk = Owner.verify_zk_proof(req['sender_address'], req['challenge_context'], req['proof_nizkp'])
                is_vc = Owner.verify_vc_issuer(req['vc'])

                # ---------------------------------------------------------
                # 🔥 NEW: TRUST POLICY ENFORCEMENT (SEPARATION OF ENTITIES)
                # ---------------------------------------------------------
                # We identify the RI by their specific DID (from setup 2_ri_node.py)
                # In a real app, this is hardcoded or fetched from a Governance Smart Contract.
                
                # Fetch issuer from the incoming VC
                issuer_did = req['vc']['payload']['issuer']
                
                # Get RI's DID (We know RI is Index 1)
                ri_key = get_ganache_key(1)
                ri_real_did = SSIEntity("RI", ri_key).did
                
                is_policy_valid = True
                if issuer_did != ri_real_did:
                    print(f"[{owner_name}] ❌ Policy Violation: Issuer {issuer_did} is NOT the Research Institute.")
                    print(f"[{owner_name}]    > Only the RI can authorize Data Analysts.")
                    is_policy_valid = False
                # ---------------------------------------------------------

                # --- STEP B: CHECK MERKLE STATUS ---
                is_merkle_valid = False
                try:
                    vc_string = json.dumps(req['vc'], sort_keys=True)
                    proof = req.get('merkle_proof')
                    if proof:
                        blockchain_root = contract.functions.getMerkleRoot(issuer_did).call()
                        if blockchain_root:
                            is_merkle_valid = verify_merkle_proof(vc_string, proof, blockchain_root)
                except:
                    pass

                # --- DECISION ---
                if is_zk and is_vc and is_merkle_valid and is_policy_valid:
                    print(f"[{owner_name}] ✅ Trusted Analyst (Identity + Merkle + Policy Valid).")
                    # ------------------------------------------------------------------
                    # 🔥 NEW STEP: SELF-DIAGNOSTIC (AM I BANNED?)
                    # ------------------------------------------------------------------
                    print(f"[{owner_name}] 🛡️ Performing Self-Diagnostic on License...")
                    try:
                        # 1. Load my own proof
                        my_proof_file = f"merkle_proof_owner_{owner_index}.json"
                        if os.path.exists(my_proof_file):
                            my_proof = load_json(my_proof_file)
                            
                            # 2. Get the *LIVE* Root from Blockchain (LG's Root)
                            my_issuer_did = my_vc['payload']['issuer']
                            live_root = contract.functions.getMerkleRoot(my_issuer_did).call()
                            
                            # 3. Verify myself
                            my_vc_string = json.dumps(my_vc, sort_keys=True)
                            am_i_valid = verify_merkle_proof(my_vc_string, my_proof, live_root)
                            
                            if not am_i_valid:
                                print("\n" + "!"*60)
                                print(f"[{owner_name}] ⛔ CRITICAL ALERT: HOSPITAL LICENSE REVOKED!")
                                print(f"[{owner_name}] ❌ The Government has removed you from the Trust List.")
                                print(f"[{owner_name}] 🛑 Aborting Training. Access Denied.")
                                print("!"*60 + "\n")
                                continue # <--- STOP HERE. DO NOT TRAIN.
                            else:
                                print(f"[{owner_name}] ✅ License Active. Proceeding...")
                        else:
                            print(f"[{owner_name}] ⚠️ No proof file found to self-check.")
                    except Exception as e:
                        print(f"[{owner_name}] ⚠️ Self-Check Error: {e}")
                    # ------------------------------------------------------------------

                    # --- STEP C: AUDIT LOG ---
                    print(f"[{owner_name}] 📝 Logging to KAC Audit System...")
                    try:
                        tx = contract.functions.logAudit(Owner.did, sender_did, "TRAINING_AUTH_SUCCESS").build_transaction({
                            'from': Owner.address,
                            'nonce': w3.eth.get_transaction_count(Owner.address),
                            'gas': 3000000,
                            'gasPrice': w3.to_wei('20', 'gwei')
                        })
                        signed_tx = w3.eth.account.sign_transaction(tx, Owner.account.key)
                        w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                        print(f"[{owner_name}] ✅ Audit Logged on Blockchain.")
                    except:
                        pass

                    # --- STEP D: LOCAL TRAINING ---
                    print(f"[{owner_name}] Starting Local Training...")
                    try:
                        raw_df = pd.read_csv(dataset_file)
                        X_proc, y_proc = preprocess_data(raw_df)
                        X_priv = apply_ldp(X_proc, epsilon=2.0)
                        
                        X_tensor = torch.FloatTensor(X_priv)
                        y_tensor = torch.FloatTensor(y_proc).unsqueeze(1)
                        
                        model = HybridDL(X_priv.shape[1])
                        criterion = nn.MSELoss()
                        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
                        
                        model.train()
                        for epoch in range(100):
                            optimizer.zero_grad()
                            output = model(X_tensor)
                            loss = criterion(output, y_tensor)
                            loss.backward()
                            optimizer.step()
                            time.sleep(0.01) # GIL release
                        
                        print(f"[{owner_name}] Training Done (Loss: {loss.item():.4f}). Sending Results...")

                        local_weights = model.state_dict()
                        weights_json = {k: v.tolist() for k, v in local_weights.items()}
                        
                        reply_ctx = f"FL_ACCEPT_{int(time.time())}"
                        proof_pr_o = Owner.generate_zk_proof(reply_ctx)
                        my_proof = load_json(my_proof_file) if os.path.exists(my_proof_file) else None

                        reply_payload = {
                            "sender_did": Owner.did,
                            "sender_address": Owner.address,
                            "vc": my_vc,
                            "proof_nizkp": proof_pr_o,
                            "challenge_context": reply_ctx,
                            "weights": weights_json,
                            "meta": {"data_rows": len(X_priv)},
                            "merkle_proof": my_proof 
                        }

                        cloud.send(sender_did, "M2", reply_payload)
                        print(f"[{owner_name}] 📤 Sent M2 Reply (with Proof) to Analyst.")
                        
                    except Exception as e:
                        print(f"❌ Training Error: {e}")

                else:
                    print(f"[{owner_name}] ❌ Security Failed.")

            except Exception as e:
                print(f"[{owner_name}] ❌ Verification Error: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python 5_owner_node.py <OWNER_INDEX>")
    else:
        idx = int(sys.argv[1])
        run_owner_node(idx)