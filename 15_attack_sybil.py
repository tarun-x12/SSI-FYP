import time
from ssi_utils import SSIEntity, load_json
from key_manager import get_ganache_key
from cloud_client import CloudAgentClient

def run_sybil_attack():
    print("\n" + "="*60)
    print("      ⚔️  TEST CASE 6: THE ROGUE ISSUER (SYBIL) ATTACK      ")
    print("      (Hacker tries to join with a Self-Signed VC)")
    print("="*60)
    
    config = load_json("system_config.json")

    # 1. CREATE A HACKER (The "Rogue Issuer")
    hacker_key = get_ganache_key(9) 
    Hacker = SSIEntity("Dr. Evil", hacker_key, config['contract_address'])
    
    # 2. HACKER ISSUES A CREDENTIAL TO THEMSELVES
    # The signature is mathematically valid, but the Issuer is NOT the Gov.
    print("[Attack] Generating Self-Signed Credential...")
    vc_fake = Hacker.issue_credential(
        holder_did=Hacker.did,
        holder_address=Hacker.address,
        claims={"role": "Authorized Hospital", "clearance": "High"}
    )
    
    # 3. TRY TO CONNECT TO THE ANALYST
    # We need to find the Analyst's DID
    try:
        vc_analyst = load_json("vc_analyst.json")
        target_did = vc_analyst['payload']['credentialSubject']['id']
    except:
        print("❌ Error: Analyst VC not found.")
        return

    def on_reply(msg): pass
    cloud = CloudAgentClient(Hacker.did, on_reply)
    cloud.connect()

    print(f"[Attack] Sending Fake Model Update to Analyst {target_did}...")
    
    # Fake payload simulating a Model Update (M2)
    payload = {
        "sender_did": Hacker.did,
        "sender_address": Hacker.address,
        "vc": vc_fake, 
        "proof_nizkp": Hacker.generate_zk_proof("test"),
        "challenge_context": "test",
        "weights": {}, # Empty weights
        "meta": {"data_rows": 100},
        "merkle_proof": [] 
    }

    cloud.send(target_did, "M2", payload)
    print("[Attack] Malicious Update Sent. Watch Analyst Terminal!")
    time.sleep(3)

if __name__ == "__main__":
    run_sybil_attack()