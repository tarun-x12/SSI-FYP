from ssi_utils import SSIEntity, load_json, save_json, w3
from key_manager import get_ganache_key

# Load Config
config = load_json("system_config.json")

# 1. SETUP KEYS AUTOMATICALLY
PKEY_RI = get_ganache_key(1) # Index 1
PKEY_GA = get_ganache_key(0) # Index 0
PKEY_ANALYST = get_ganache_key(3) # Index 3 (Needed to issue VC to Analyst)

RI = SSIEntity("Research Institute", PKEY_RI, config['contract_address'])
RI.register_on_blockchain()

# --- GA Issues VC to RI ---
print("\n--- [GA] Issuing VC to RI ---")
GA = SSIEntity("GA_Signer", PKEY_GA, config['contract_address'])

vc_ga_to_ri = GA.issue_credential(RI.did, RI.address, {"role": "Authorized Institute"})
save_json("vc_ri.json", vc_ga_to_ri)

if RI.verify_credential(vc_ga_to_ri, config['ga_address']):
    print("[RI] Successfully received and verified accreditation from GA.")

# --- CRITICAL MISSING STEP: RI Issues VC to Analyst ---
print("\n--- [RI] Issuing VC to Data Analyst ---")
# We need the Analyst's DID to issue it to them
temp_analyst = SSIEntity("Temp_Analyst", PKEY_ANALYST) 

vc_ri_to_analyst = RI.issue_credential(
    holder_did=temp_analyst.did, 
    holder_address=temp_analyst.address, 
    claims={"access_level": "researcher", "clearance": "high"}
)
save_json("vc_analyst.json", vc_ri_to_analyst)
print("[RI] Issued VC to Analyst (Saved to vc_analyst.json)")