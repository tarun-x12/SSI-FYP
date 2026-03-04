import time
import glob
import torch
import json
import os
from ssi_utils import SSIEntity, load_json, w3
from key_manager import get_ganache_key
from cloud_client import CloudAgentClient
from merkle_utils import verify_merkle_proof
from fl_utils import HybridDL

incoming_replies = []

MODEL_LATEST = "global_model_final.pth"


def on_reply_received(msg):

    if msg.get("type") == "M2":

        sender = msg["from"]

        print(f"\n📩 Received M2 from {sender}")

        incoming_replies.append(msg["payload"])


def get_next_version():

    version = 1

    while os.path.exists(f"global_model_v{version}.pth"):
        version += 1

    return version


def run_persistent_analyst():

    try:
        config = load_json("system_config.json")
    except:
        print("system_config.json missing")
        return

    PKEY_A = get_ganache_key(3)

    Analyst = SSIEntity("Data Analyst", PKEY_A, config["contract_address"])

    print("[Analyst] Ensuring blockchain registration")

    try:
        Analyst.register_on_blockchain()
    except:
        pass

    cloud = CloudAgentClient(Analyst.did, on_reply_received)

    cloud.connect()

    print("\n--- Phase 1: Discover Owners ---")

    owner_files = glob.glob("vc_owner_*.json")

    if len(owner_files) == 0:

        print("No owner VCs found")

        return

    print(f"Discovered {len(owner_files)} owners")

    challenge = f"FL_SESSION_{int(time.time())}"

    proof = Analyst.generate_zk_proof(challenge)

    vc_analyst = load_json("vc_analyst.json")

    merkle_proof = None

    try:
        merkle_proof = load_json("merkle_proof_analyst.json")
    except:
        pass

    payload = {

        "sender_did": Analyst.did,
        "sender_address": Analyst.address,
        "vc": vc_analyst,
        "proof_nizkp": proof,
        "challenge_context": challenge,
        "merkle_proof": merkle_proof,
    }

    sent = 0

    for file in owner_files:

        owner = load_json(file)

        vc_payload = owner["payload"]

        if "credentialSubject" in vc_payload:
            target_did = vc_payload["credentialSubject"]["id"]
        else:
            target_did = vc_payload["holder"]

        print(f"Sending request to {target_did}")

        cloud.send(target_did, "M1", payload)

        sent += 1

    print("\n--- Phase 2: Waiting for replies ---")

    while len(incoming_replies) < sent:

        print(f"\rReceived {len(incoming_replies)}/{sent} updates", end="")

        time.sleep(2)

    print("\nReceived all updates")

    print("\n--- Phase 3: Aggregation ---")

    verified_updates = []

    contract = w3.eth.contract(
        address=config["contract_address"], abi=config["abi"]
    )

    for reply in incoming_replies:

        sender = reply["sender_did"]

        try:

            is_zk = Analyst.verify_zk_proof(
                reply["sender_address"],
                reply["challenge_context"],
                reply["proof_nizkp"],
            )

            is_vc = Analyst.verify_vc_issuer(reply["vc"])

            vc_string = json.dumps(reply["vc"], sort_keys=True)

            proof = reply.get("merkle_proof")

            issuer = reply["vc"]["payload"]["issuer"]

            root = contract.functions.getMerkleRoot(issuer).call()

            is_merkle = False

            if proof and root:

                is_merkle = verify_merkle_proof(vc_string, proof, root)

            if is_zk and is_vc and is_merkle:

                print(f"Verified update from {sender}")

                verified_updates.append(reply)

            else:

                print(f"Rejected update from {sender}")

        except Exception as e:

            print("Verification error:", e)

    if len(verified_updates) == 0:

        print("No valid updates")

        return

    first_weights = verified_updates[0]["weights"]

    first_tensor = torch.tensor(list(first_weights.values())[0])

    if len(first_tensor.shape) > 1:
        input_dim = first_tensor.shape[1]
    else:
        input_dim = first_tensor.shape[0]

    model = HybridDL(input_dim)

    if os.path.exists(MODEL_LATEST):

        print("Loading existing global model")

        model.load_state_dict(torch.load(MODEL_LATEST), strict=False)

    else:

        print("No pretrained model found")

    agg_weights = {}

    total_samples = 0

    for update in verified_updates:

        local_weights = {k: torch.tensor(v) for k, v in update["weights"].items()}

        samples = update["meta"]["data_rows"]

        if not agg_weights:

            for k in local_weights:

                agg_weights[k] = local_weights[k] * samples

        else:

            for k in agg_weights:

                agg_weights[k] += local_weights[k] * samples

        total_samples += samples

    for k in agg_weights:

        agg_weights[k] = agg_weights[k] / total_samples

    model.load_state_dict(agg_weights, strict=False)

    version = get_next_version()

    version_file = f"global_model_v{version}.pth"

    torch.save(model.state_dict(), version_file)

    torch.save(model.state_dict(), MODEL_LATEST)

    print(f"\nGlobal model updated")

    print(f"Saved version: {version_file}")

    print("Updated global_model_final.pth")


if __name__ == "__main__":

    run_persistent_analyst()