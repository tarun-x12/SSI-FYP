from ssi_utils import SSIEntity, load_json, save_json
from key_manager import get_ganache_key

config = load_json("system_config.json")
PKEY_LG = get_ganache_key(2) # Index 2 for Local Gov
PKEY_GA = get_ganache_key(0) # Index 0 for GA

LG = SSIEntity("Local Government", PKEY_LG, config['contract_address'])
LG.register_on_blockchain()

# --- GA Issues VC to LG (Same as before) ---
# For simulation speed, we assume LG is already authorized by GA from previous runs
# or we can mock the GA signature here if needed. 
# We will focus on LG issuing to the 3 Owners.

print("\n--- [LG] Issuing VCs to 3 Data Owners ---")

# Define the 3 Owners' Private Keys (To derive addresses/DIDs)
# In reality, Owners send their DIDs to LG. Here we simulate knowing them.
owner_keys = [
    get_ganache_key(4), # Owner 1
    get_ganache_key(5), # Owner 2
    get_ganache_key(6)  # Owner 3
]

owner_vcs = []

for i, key in enumerate(owner_keys):
    # Create temp entity to get the address/DID correctly
    temp_owner = SSIEntity(f"Owner_{i+1}", key)
    
    # LG Issues VC
    # Claims can be specific (e.g., Hospital A, Hospital B, Clinic C)
    claims = {
        "role": "Data Provider", 
        "region": f"Region_{i+1}", 
        "data_type": "Medical_IoT"
    }
    
    vc = LG.issue_credential(temp_owner.did, temp_owner.address, claims)
    
    # Save individual VC files
    filename = f"vc_owner_{i+1}.json"
    save_json(filename, vc)
    owner_vcs.append(vc)

print(f"[LG] Issued {len(owner_vcs)} VCs. Owners can now verify themselves.")