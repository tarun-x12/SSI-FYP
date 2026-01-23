from ssi_utils import SSIEntity, load_json, save_json, w3
from key_manager import get_ganache_key
from merkle_utils import MerkleTree
import json

# Load Config
config = load_json("system_config.json")

# --- FORCE LOAD CONTRACT WITH CORRECT ABI ---
# We define this locally to ensure we are using the LATEST ABI from system_config.json
# instead of relying on potentially stale cache in ssi_utils.
contract = w3.eth.contract(address=config['contract_address'], abi=config['abi'])

# Setup Keys
PKEY_RI = get_ganache_key(1)
PKEY_GA = get_ganache_key(0)
PKEY_ANALYST = get_ganache_key(3)

# 1. RI Register
print("\n--- [RI] Booting Up & Registering ---")
RI = SSIEntity("Research Institute", PKEY_RI, config['contract_address'])
RI.register_on_blockchain()

# 2. GA Issues VC to RI
print("\n--- [GA] Issuing VC to RI ---")
GA = SSIEntity("GA_Signer", PKEY_GA, config['contract_address'])
vc_ga_to_ri = GA.issue_credential(RI.did, RI.address, {"role": "Authorized Institute"})
save_json("vc_ri.json", vc_ga_to_ri)

# 3. RI Issues VC to Analyst
print("\n--- [RI] Issuing VC to Data Analyst ---")
temp_analyst = SSIEntity("Data Analyst", PKEY_ANALYST, config['contract_address'])
temp_analyst.register_on_blockchain()

vc_ri_to_analyst = RI.issue_credential(
    holder_did=temp_analyst.did, 
    holder_address=temp_analyst.address, 
    claims={"access_level": "researcher", "clearance": "high"}
)
save_json("vc_analyst.json", vc_ri_to_analyst)
print("[RI] Issued VC to Analyst.")

# --- NOVELTY: HBMT MANAGER (Generate Merkle Tree) ---
print("\n--- [HBMT] Generating Merkle Tree for Validity ---")

# In a real system, this list would have thousands of VCs.
vc_string = json.dumps(vc_ri_to_analyst, sort_keys=True)
valid_vcs = [vc_string, "dummy_data_1", "dummy_data_2"] 

# Build Tree
mt = MerkleTree(valid_vcs)
root = mt.get_root()
proof = mt.get_proof(vc_string)

print(f"[HBMT] Merkle Root Generated: {root[:10]}...")

# 4. PUBLISH ROOT (Using the forced contract instance)
try:
    print(f"[HBMT] Publishing to Smart Contract at {config['contract_address']}...")
    tx = contract.functions.publishMerkleRoot(RI.did, root).build_transaction({
        'from': RI.address,
        'nonce': w3.eth.get_transaction_count(RI.address),
        'gas': 3000000,
        'gasPrice': w3.to_wei('20', 'gwei')
    })
    signed_tx = w3.eth.account.sign_transaction(tx, RI.account.key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print("[HBMT] ✅ Merkle Root Published to Blockchain Ledger.")
except Exception as e:
    print(f"❌ Error publishing root: {e}")
    # Print available functions to debug
    print("DEBUG: Available functions in ABI:", [f.fn_name for f in contract.functions])

# Save Proof for Analyst
save_json("merkle_proof_analyst.json", proof)
print("[HBMT] Merkle Proof issued to Analyst.")