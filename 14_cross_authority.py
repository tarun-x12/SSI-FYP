import time
import json
from ssi_utils import SSIEntity, load_json
from key_manager import get_ganache_key
from cloud_client import CloudAgentClient
from relay_keepalive import start_relay_keepalive


def run_cross_authority_attack():

    print("\n" + "="*60)
    print("      SECURITY TEST: CROSS-AUTHORITY ATTACK")
    print("="*60)

    config = load_json("system_config.json")

    # -------------------------------------
    # 1. AUTHENTICATE AS LOCAL GOVERNMENT
    # -------------------------------------

    print("[Attack] Authenticating as Local Government")

    lg_key = get_ganache_key(2)

    LG = SSIEntity(
        "Local Government",
        lg_key,
        config["contract_address"]
    )

    # -------------------------------------
    # 2. CREATE FAKE ANALYST
    # -------------------------------------

    print("[Attack] Creating Fake Analyst identity")

    fake_key = get_ganache_key(9)

    FakeAnalyst = SSIEntity(
        "Fake Analyst",
        fake_key,
        config["contract_address"]
    )

    try:
        FakeAnalyst.register_on_blockchain()
    except:
        pass

    print("[Attack] Fake Analyst DID:", FakeAnalyst.did)

    # -------------------------------------
    # 3. LG ISSUES FRAUDULENT VC
    # -------------------------------------

    print("[Attack] LG issuing Analyst Credential (Policy Violation)")

    vc_fake = LG.issue_credential(

        holder_did=FakeAnalyst.did,
        holder_address=FakeAnalyst.address,

        claims={
            "access_level": "researcher",
            "clearance": "Top Secret"
        }

    )

    # -------------------------------------
    # 4. CONNECT TO CLOUD RELAY
    # -------------------------------------

    def on_reply(msg):

        print("\n[Attack Result] Reply received:")
        print(msg)

    cloud = CloudAgentClient(FakeAnalyst.did, on_reply)

    print("[Attack] Connecting to Cloud Relay")

    cloud.connect()

    print("[Cloud] Connected to Relay")
    print("[Cloud] Ready for Secure Messaging")

    # start keepalive
    start_relay_keepalive(cloud)

    # -------------------------------------
    # 5. FIND TARGET OWNER
    # -------------------------------------

    try:

        owner_vc = load_json("vc_owner_1.json")

        target_did = owner_vc["payload"]["credentialSubject"]["id"]

    except:

        print("Could not find Owner VC file")

        return

    print("[Attack] Target Owner:", target_did)

    # -------------------------------------
    # 6. PREPARE MALICIOUS REQUEST
    # -------------------------------------

    challenge_msg = f"FL_SESSION_{int(time.time())}"

    proof_pr = FakeAnalyst.generate_zk_proof(challenge_msg)

    payload = {

        "sender_did": FakeAnalyst.did,
        "sender_address": FakeAnalyst.address,

        # Fraudulent credential
        "vc": vc_fake,

        "proof_nizkp": proof_pr,
        "challenge_context": challenge_msg,

        # Fake Merkle proof
        "merkle_proof": []

    }

    # -------------------------------------
    # 7. SEND ATTACK REQUEST
    # -------------------------------------

    print("[Attack] Sending malicious training request")

    cloud.send(target_did, "M1", payload)

    print("\nAttack request sent.")
    print("Watch the Owner terminal for rejection.")

    # wait for response
    time.sleep(10)


if __name__ == "__main__":

    run_cross_authority_attack()