import time
import glob
import torch
import json
import os
import pandas as pd

from ssi_utils import SSIEntity, load_json, w3
from key_manager import get_ganache_key
from cloud_client import CloudAgentClient
from merkle_utils import verify_merkle_proof
from fl_utils import HybridDL


MODEL_LATEST = "global_model_final.pth"
METRICS_FILE = "fl_training_metrics.csv"

incoming_replies = []


def on_reply_received(msg):

    if msg.get("type") == "M2":

        sender = msg["from"]

        print("\n[Cloud] Model update received from:", sender)

        incoming_replies.append(msg["payload"])


def run_persistent_analyst():

    try:
        config = load_json("system_config.json")
    except:
        print("system_config.json missing")
        return


    print("\n====================================")
    print("Federated Analyst Node Started")
    print("====================================")


    PKEY_A = get_ganache_key(3)

    Analyst = SSIEntity("Data Analyst", PKEY_A, config["contract_address"])


    try:
        Analyst.register_on_blockchain()
    except:
        pass


    cloud = CloudAgentClient(Analyst.did, on_reply_received)

    cloud.connect()


    owner_files = glob.glob("vc_owner_*.json")

    if len(owner_files) == 0:

        print("No owner VCs found")

        return


    print(f"[Discovery] Found {len(owner_files)} dataset owners")


    round_number = 1


    while True:

        print("\n====================================")
        print(f"Federated Round {round_number}")
        print("====================================")

        incoming_replies.clear()

        start_round_time = time.time()


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

        print("\n[FL] Sending training requests to owners")

        for file in owner_files:

            owner = load_json(file)

            vc_payload = owner["payload"]

            if "credentialSubject" in vc_payload:
                target_did = vc_payload["credentialSubject"]["id"]
            else:
                target_did = vc_payload["holder"]

            print("Request sent to:", target_did)

            cloud.send(target_did, "M1", payload)

            sent += 1


        print("\n[FL] Waiting for client updates")

        while len(incoming_replies) < sent:

            print(
                f"\rReceived {len(incoming_replies)}/{sent} updates",
                end=""
            )

            time.sleep(2)


        print("\n[FL] All updates received")


        print("\n[Verification] Checking updates")

        verified_updates = []

        rejected_updates = 0

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

                    is_merkle = verify_merkle_proof(
                        vc_string,
                        proof,
                        root
                    )

                if is_zk and is_vc and is_merkle:

                    print("Verified update from:", sender)

                    verified_updates.append(reply)

                else:

                    print("Rejected update from:", sender)

                    rejected_updates += 1

            except Exception as e:

                print("Verification error:", e)


        if len(verified_updates) == 0:

            print("No valid updates received")

            time.sleep(10)

            continue


        print("\n[Aggregation] Starting Federated Averaging")


        first_weights = verified_updates[0]["weights"]

        first_tensor = torch.tensor(list(first_weights.values())[0])


        if len(first_tensor.shape) > 1:
            input_dim = first_tensor.shape[1]
        else:
            input_dim = first_tensor.shape[0]


        model = HybridDL(input_dim)


        if os.path.exists(MODEL_LATEST):

            print("[Model] Loading previous global model")

            model.load_state_dict(torch.load(MODEL_LATEST), strict=False)


        agg_weights = {}

        total_samples = 0


        print("\n[Client Contributions]")

        for update in verified_updates:

            local_weights = {

                k: torch.tensor(v)

                for k, v in update["weights"].items()

            }

            samples = update["meta"]["data_rows"]

            print(update["sender_did"], ":", samples, "samples")

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

        torch.save(model.state_dict(), MODEL_LATEST)


        aggregation_time = time.time() - start_round_time

        avg_samples = total_samples / len(verified_updates)


        param_count = sum(p.numel() for p in model.parameters())

        model_size = os.path.getsize(MODEL_LATEST) / 1024


        print("\n====================================")
        print("Federated Round Summary")
        print("====================================")

        print("Participating Clients:", len(verified_updates))
        print("Rejected Clients:", rejected_updates)
        print("Total Training Samples:", total_samples)
        print("Average Samples per Client:", int(avg_samples))
        print("Aggregation Time:", round(aggregation_time, 2), "seconds")
        print("Model Parameters:", param_count)
        print("Model Size:", round(model_size, 2), "KB")

        print("\nGlobal Model Updated:", MODEL_LATEST)


        metrics = {

            "round": round_number,
            "clients": len(verified_updates),
            "rejected": rejected_updates,
            "total_samples": total_samples,
            "avg_samples": avg_samples,
            "aggregation_time": aggregation_time,
            "model_size_kb": model_size

        }


        df = pd.DataFrame([metrics])


        if os.path.exists(METRICS_FILE):

            old = pd.read_csv(METRICS_FILE)

            df = pd.concat([old, df], ignore_index=True)


        df.to_csv(METRICS_FILE, index=False)


        print("\n[Metrics] Saved to", METRICS_FILE)


        round_number += 1


        print("\nNext round starting in 15 seconds")

        time.sleep(15)


if __name__ == "__main__":

    run_persistent_analyst()