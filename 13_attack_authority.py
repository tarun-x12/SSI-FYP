import json
from ssi_utils import SSIEntity, load_json, w3
from key_manager import get_ganache_key

def attempt_coup():
    print("\n" + "="*60)
    print("      ⚔️  SECURITY TEST: FAKE AUTHORITY ATTACK      ")
    print("="*60)

    # 1. SETUP
    try:
        config = load_json("system_config.json")
        contract = w3.eth.contract(address=config['contract_address'], abi=config['abi'])
    except Exception as e:
        print(f"❌ Error loading system: {e}")
        return

    # 2. CREATE HACKER IDENTITY
    # We use a random key (Index 9) that is NOT the LG (Index 2)
    hacker_key = get_ganache_key(9)
    Hacker = SSIEntity("Anonymous Hacker", hacker_key, config['contract_address'])
    print(f"[Hacker] Generated Identity: {Hacker.did}")
    
    # 3. ATTEMPT TO OVERWRITE MERKLE ROOT
    print("[Hacker] Attempting to overwrite Hospital Trust Root...")
    fake_root = "0xDEADBEEF00000000000000000000000000000000000000000000000000000000"
    
    try:
        # This function should ONLY allow the real Local Gov
        tx = contract.functions.publishMerkleRoot(Hacker.did, fake_root).build_transaction({
            'from': Hacker.address,
            'nonce': w3.eth.get_transaction_count(Hacker.address),
            'gas': 3000000,
            'gasPrice': w3.to_wei('20', 'gwei')
        })
        signed_tx = w3.eth.account.sign_transaction(tx, Hacker.account.key)
        
        # This line should fail if your Smart Contract has security (e.g. require msg.sender == owner)
        # Note: If your current solidity contract is basic, this might succeed, 
        # which exposes a vulnerability we need to fix!
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print("\n❌ CRITICAL FAILURE: The Hacker successfully overwrote the Root!")
        print("   -> Your Smart Contract lacks 'Access Control'.")

    except Exception as e:
        print("\n✅ SECURITY SUCCESS: The Blockchain rejected the transaction.")
        print(f"   Reason: {e}")
        print("   -> The Smart Contract correctly enforces that ONLY the LG can update roots.")

if __name__ == "__main__":
    attempt_coup()