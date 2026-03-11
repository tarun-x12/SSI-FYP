import time
import json
from ssi_utils import SSIEntity, load_json
from key_manager import get_ganache_key
from cloud_client import CloudAgentClient
from relay_keepalive import start_relay_keepalive


def run_impersonator_attack():

    print("\n" + "="*60)
    print("      TEST CASE: IMPERSONATOR ATTACK")
    print("      (Hacker steals a VC but lacks private key)")
    print("="*60)

    config = load_json("system_config.json")

    # --------------------------------------
    # 1. STEAL OWNER CREDENTIAL
    # --------------------------------------

    try:

        stolen_vc = load_json("vc_owner_1.json")

        target_did = stolen_vc["payload"]["credentialSubject"]["id"]

        print("[Hacker] Stolen Credential for:", target_did)

    except:

        print("Error: vc_owner_1.json not found")
        return

    # steal merkle proof

    try:
        stolen_merkle = load_json("merkle_proof_owner_1.json")
    except:
        print("Warning: Merkle proof not found")
        stolen_merkle = []

    # extract victim address

    target_address = target_did.split(":")[-1]

    # --------------------------------------
    # 2. CREATE HACKER IDENTITY
    # --------------------------------------

    hacker_key = get_ganache_key(9)

    Hacker = SSIEntity(
        "Identity Thief",
        hacker_key,
        config["contract_address"]
    )

    print("[Hacker] Fake identity created")
    print("[Hacker] Address:", Hacker.address)

    # --------------------------------------
    # 3. HANDLE ANALYST CHALLENGE
    # --------------------------------------

    def on_request(msg):

        if msg.get("type") == "M1":

            sender_did = msg["from"]

            challenge = msg["payload"]["challenge_context"]

            print("\n[Hacker] Challenge received:", challenge)

            print("[Hacker] Signing with WRONG private key")

            fake_proof = Hacker.generate_zk_proof(challenge)

            reply_payload = {

                "sender_did": target_did,
                "sender_address": target_address,

                "vc": stolen_vc,

                "proof_nizkp": fake_proof,
                "challenge_context": challenge,

                "weights": {"layer1": [0.0]},
                "meta": {"data_rows": 100},

                "merkle_proof": stolen_merkle

            }

            cloud.send(sender_did, "M2", reply_payload)

            print("[Hacker] Fake proof sent to analyst")

    # --------------------------------------
    # 4. CONNECT TO CLOUD RELAY
    # --------------------------------------

    cloud = CloudAgentClient(target_did, on_request)

    print("[Hacker] Connecting to Cloud Relay")

    cloud.connect()

    print("[Cloud] Connected to Cloud Relay")
    print("[Cloud] Ready for Secure Messaging")

    # start relay keepalive
    start_relay_keepalive(cloud)

    print("[Hacker] Waiting for analyst request...")

    try:

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":

    run_impersonator_attack()