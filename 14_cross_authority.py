import time
import json
from ssi_utils import SSIEntity, load_json, save_json
from key_manager import get_ganache_key
from cloud_client import CloudAgentClient

def run_cross_authority_attack():
    print("\n" + "="*60)
    print("      ⚔️  SECURITY TEST: CROSS-AUTHORITY ATTACK      ")
    print("="*60)
    
    config = load_json("system_config.json")

    # 1. SETUP: WE ARE THE LOCAL GOVERNMENT (LG)
    print("[Attack] Authenticating as Local Government (Index 2)...")
    lg_key = get_ganache_key(2)
    LG = SSIEntity("Local Government", lg_key, config['contract_address'])
    
    # 2. CREATE A FAKE ANALYST
    print("[Attack] Creating 'Fake Analyst' Identity...")
    fake_key = get_ganache_key(9)
    FakeAnalyst = SSIEntity("Fake Analyst", fake_key, config['contract_address'])
    FakeAnalyst.register_on_blockchain()

    # 3. LG ISSUES AN ANALYST CREDENTIAL (THE VIOLATION)
    print("[Attack] LG is fraudulently issuing an 'Analyst Clearance' VC...")
    vc_fake = LG.issue_credential(
        holder_did=FakeAnalyst.did,
        holder_address=FakeAnalyst.address,
        claims={"access_level": "researcher", "clearance": "Top Secret"}
    )
    # Note: LG is signing this, NOT RI.
    
    # 4. SEND TO OWNER 1
    print("[Attack] Connecting to Cloud Relay...")
    
    def on_reply(msg):
        print(f"\n[Result] Received Reply: {msg}")

    cloud = CloudAgentClient(FakeAnalyst.did, on_reply)
    cloud.connect()

    # Find Target DID (Owner 1)
    try:
        owner_vc = load_json("vc_owner_1.json")
        target_did = owner_vc['payload']['credentialSubject']['id']
    except:
        print("❌ Could not find Owner 1 VC file.")
        return

    print(f"[Attack] Sending Malicious Request to {target_did}...")
    
    challenge_msg = f"FL_SESSION_{int(time.time())}"
    proof_pr = FakeAnalyst.generate_zk_proof(challenge_msg)

    payload = {
        "sender_did": FakeAnalyst.did,
        "sender_address": FakeAnalyst.address,
        "vc": vc_fake, # <--- The LG-Signed Analyst VC
        "proof_nizkp": proof_pr,
        "challenge_context": challenge_msg,
        "merkle_proof": [] # Empty/Fake proof
    }

    cloud.send(target_did, "M1", payload)
    
    print("[Attack] Request Sent. Watch the Owner Terminal for rejection!")
    time.sleep(5) 

if __name__ == "__main__":
    run_cross_authority_attack()