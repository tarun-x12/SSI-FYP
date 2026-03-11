import sys
import os
import torch
import torch.nn as nn
import pandas as pd
import time
import json
import numpy as np
import random

from ssi_utils import SSIEntity, load_json, get_contract, w3
from key_manager import get_ganache_key
from fl_utils import HybridDL, preprocess_data, apply_ldp
from cloud_client import CloudAgentClient
from merkle_utils import verify_merkle_proof
from relay_keepalive import start_relay_keepalive

SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)
random.seed(SEED)

incoming_requests = []


def on_request_received(msg):

    if msg.get("type") == "M1":

        print("\n===================================")
        print("[Cloud] Federated Training Request Received")
        print("From:", msg["from"])
        print("===================================\n")

        incoming_requests.append(msg)


def run_owner_node(owner_index):

    config = load_json("system_config.json")

    ganache_index = owner_index + 3
    owner_name = f"Owner_{owner_index}"

    dataset_file = f"dataset_owner_{owner_index}.csv"
    vc_filename = f"vc_owner_{owner_index}.json"

    print("\n-----------------------------------")
    print(f"Booting {owner_name}")
    print("-----------------------------------")

    pkey = get_ganache_key(ganache_index)

    Owner = SSIEntity(owner_name, pkey, config["contract_address"])

    try:

        print("[Blockchain] Registering DID on chain...")
        Owner.register_on_blockchain()
        print("[Blockchain] Registration complete")

    except Exception as e:

        print("[Blockchain] Registration warning:", e)

    if not os.path.exists(vc_filename):

        print("[Error] VC file missing")
        return

    my_vc = load_json(vc_filename)

    cloud = CloudAgentClient(Owner.did, on_request_received)

    cloud.connect()

    print("[Cloud] Connected to Cloud Relay")
    print("[Cloud] Ready for Secure Messaging")

    # -------------------------------
    # START RELAY KEEPALIVE
    # -------------------------------
    start_relay_keepalive(cloud)

    contract = get_contract(config["contract_address"])

    print(f"\n[{owner_name}] Node started")
    print(f"[{owner_name}] DID:", Owner.did)
    print(f"[{owner_name}] Dataset:", dataset_file)
    print(f"[{owner_name}] Waiting for FL requests...\n")

    while True:

        if len(incoming_requests) > 0:

            msg = incoming_requests.pop(0)

            req = msg["payload"]
            sender_did = msg["from"]

            print("\n-----------------------------------")
            print(f"[{owner_name}] Analyst request received")
            print("-----------------------------------")

            print("[Security] Verifying analyst identity...")

            try:

                is_zk = Owner.verify_zk_proof(
                    req["sender_address"],
                    req["challenge_context"],
                    req["proof_nizkp"]
                )

                print("[Security] ZK Proof:", is_zk)

                is_vc = Owner.verify_vc_issuer(req["vc"])
                print("[Security] VC Valid:", is_vc)

                issuer_did = req["vc"]["payload"]["issuer"]

                ri_key = get_ganache_key(1)
                ri_real_did = SSIEntity("RI", ri_key).did

                is_policy_valid = issuer_did == ri_real_did
                print("[Security] Issuer Policy Valid:", is_policy_valid)

                # -------------------------------
                # MERKLE LICENSE CHECK
                # -------------------------------
                is_merkle_valid = False

                try:

                    vc_string = json.dumps(my_vc, sort_keys=True)

                    proof_file = f"merkle_proof_owner_{owner_index}.json"

                    proof = load_json(proof_file) if os.path.exists(proof_file) else None

                    if proof:

                        lg_key = get_ganache_key(2)
                        lg_did = SSIEntity("Local Government", lg_key).did

                        blockchain_root = contract.functions.getMerkleRoot(
                            lg_did
                        ).call()

                        if blockchain_root:

                            is_merkle_valid = verify_merkle_proof(
                                vc_string,
                                proof,
                                blockchain_root
                            )

                except Exception as e:
                    print("[Merkle Check Error]:", e)

                print("[Security] Merkle Proof Valid:", is_merkle_valid)

                if not is_merkle_valid:

                    print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    print("[Owner] LICENSE REVOKED – ACCESS DENIED")
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")

                    continue

                if is_zk and is_vc and is_merkle_valid and is_policy_valid:

                    print("\n[Security] Analyst Trusted")

                    print("[FL] Starting Local Training")

                    raw_df = pd.read_csv(dataset_file)

                    X_proc, y_proc = preprocess_data(raw_df)

                    X_priv = apply_ldp(X_proc, epsilon=2.0)

                    X_tensor = torch.FloatTensor(X_priv)
                    y_tensor = torch.FloatTensor(y_proc).unsqueeze(1)

                    model = HybridDL(X_priv.shape[1])

                    criterion = nn.BCELoss()
                    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

                    model.train()

                    for epoch in range(100):

                        optimizer.zero_grad()

                        output = model(X_tensor)

                        loss = criterion(output, y_tensor)

                        loss.backward()
                        optimizer.step()

                        if epoch % 20 == 0:

                            print(
                                f"[Training] Epoch {epoch} | Loss {loss.item():.4f}"
                            )

                    print(f"[Training] Completed (Loss={loss.item():.4f})")

                    local_weights = model.state_dict()

                    weights_json = {

                        k: v.tolist()
                        for k, v in local_weights.items()

                    }

                    reply_ctx = f"FL_ACCEPT_{int(time.time())}"

                    proof_pr_o = Owner.generate_zk_proof(reply_ctx)

                    proof_file = f"merkle_proof_owner_{owner_index}.json"

                    my_proof = load_json(proof_file) if os.path.exists(proof_file) else None

                    reply_payload = {

                        "sender_did": Owner.did,
                        "sender_address": Owner.address,

                        "vc": my_vc,

                        "proof_nizkp": proof_pr_o,
                        "challenge_context": reply_ctx,

                        "weights": weights_json,

                        "meta": {
                            "data_rows": len(X_priv)
                        },

                        "merkle_proof": my_proof
                    }

                    print("[Cloud] Sending model update to analyst...")

                    cloud.send(sender_did, "M2", reply_payload)

                    print("[FL] Model update sent successfully")

                else:

                    print("[Security] Verification failed - request rejected")

            except Exception as e:

                print("[Owner Error]:", e)

        time.sleep(1)


if __name__ == "__main__":

    if len(sys.argv) < 2:

        print("Usage: python 5_owner_node.py <OWNER_INDEX>")

    else:

        run_owner_node(int(sys.argv[1]))