import time
import json
from ssi_utils import SSIEntity, load_json
from key_manager import get_ganache_key
from cloud_client import CloudAgentClient

def run_impersonator_attack():
    print("\n" + "="*60)
    print("      🎭  TEST CASE: IMPERSONATOR ATTACK      ")
    print("      (Hacker steals a VC file but lacks the Private Key)")
    print("="*60)

    config = load_json("system_config.json")

    # 1. THE THEFT: Load a VALID Credential (Owner 1)
    try:
        stolen_vc = load_json("vc_owner_1.json")
        target_did = stolen_vc['payload']['credentialSubject']['id']
        print(f"[Hacker] 📂 Stolen Credential for: {target_did}")
        print("[Hacker]    Claims: 'Authorized Hospital'")
    except:
        print("❌ Error: vc_owner_1.json not found. Run 3_lg_node.py first.")
        return

    # 2. THE HACKER: Initialize with a DIFFERENT Key (Index 9)
    # The hacker does NOT have Owner 1's key (Index 4).
    hacker_key = get_ganache_key(9) 
    Hacker = SSIEntity("Identity Thief", hacker_key, config['contract_address'])
    
    # 3. CONNECT TO ANALYST
    print(f"[Hacker] 🔌 Connecting to Analyst as '{target_did}'...")

    def on_request(msg):
        if msg.get('type') == 'M1':
            sender_did = msg['from']
            challenge = msg['payload']['challenge_context']
            
            print(f"\n[Hacker] 📩 Received Login Challenge: '{challenge}'")
            print(f"[Hacker] 😈 Signing challenge with WRONG Private Key...")

            # --- THE ATTACK ---
            # We are generating the proof using the HACKER'S key, 
            # but we are presenting the OWNER'S Identity (target_did).
            fake_proof = Hacker.generate_zk_proof(challenge)

            # MALICIOUS PAYLOAD
            reply_payload = {
                "sender_did": target_did, # <--- CLAIMING TO BE OWNER 1
                "sender_address": Hacker.address, # (Irrelevant, Analyst looks at DID)
                "vc": stolen_vc,          # <--- USING VALID STOLEN FILE
                "proof_nizkp": fake_proof,# <--- INVALID SIGNATURE
                "challenge_context": challenge,
                "weights": {"layer1": [0.0]}, 
                "meta": {"data_rows": 100},
                "merkle_proof": [] 
            }

            cloud.send(sender_did, "M2", reply_payload)
            print("[Hacker] 📤 Fake Proof Sent. Watch Analyst Terminal!")

    # We spoof our DID to match the stolen file so the Cloud routes messages to us
    cloud = CloudAgentClient(target_did, on_request)
    cloud.connect()
    
    print("[Hacker] Waiting for Analyst to request login...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    run_impersonator_attack()