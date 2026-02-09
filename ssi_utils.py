import json
import time
import random
from web3 import Web3
from eth_account.messages import encode_defunct

# Connect to Ganache
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))

def load_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def get_contract(address):
    try:
        config = load_json("system_config.json")
        return w3.eth.contract(address=address, abi=config['abi'])
    except Exception as e:
        print(f"⚠️ Error loading contract ABI: {e}")
        return None

class SSIEntity:
    def __init__(self, name, private_key_hex, contract_address=None):
        self.name = name
        self.private_key_hex = private_key_hex
        self.account = w3.eth.account.from_key(private_key_hex)
        self.address = self.account.address
        self.did = f"did:eth:{self.address}"
        self.contract_address = contract_address
        
        # --- ZKP SETUP (RFC 3526 - 2048-bit MODP Group) ---
        self.zk_private_key = int(self.private_key_hex, 16)
        self.G = 2 
        self.P = int(
            "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
            "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
            "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
            "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
            "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE65381"
            "FFFFFFFFFFFFFFFF", 16
        )
        # Ensure key is within range
        self.zk_private_key = self.zk_private_key % (self.P - 1)
        self.zk_public_key = pow(self.G, self.zk_private_key, self.P)

    def register_on_blockchain(self):
        """Registers DID and the ZK-Public Key on Ganache"""
        if not self.contract_address:
            return

        contract = get_contract(self.contract_address)
        pub_key_str = hex(self.zk_public_key)
        
        try:
            # --- FIX: Check Registry Struct ---
            # registry(address) returns (did, pubKey, exists)
            user_data = contract.functions.registry(self.address).call()
            
            if user_data[2]: # 'exists' boolean is at index 2
                print(f"[{self.name}] ✅ Already registered on chain.")
                return

            print(f"[{self.name}] Registering {self.did}...")
            tx = contract.functions.register(self.did, pub_key_str).build_transaction({
                'from': self.address,
                'nonce': w3.eth.get_transaction_count(self.address),
                'gas': 3000000,
                'gasPrice': w3.to_wei('20', 'gwei')
            })
            signed_tx = w3.eth.account.sign_transaction(tx, self.account.key)
            
            # Wait for transaction
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            w3.eth.wait_for_transaction_receipt(tx_hash)
            
            print(f"[{self.name}] ✅ Registered Public Key on Chain.")
        except Exception as e:
            print(f"[{self.name}] ⚠️ Registration Warning: {e}")

    def issue_credential(self, holder_did, holder_address, claims):
        credential = {
            "type": ["VerifiableCredential"],
            "issuer": self.did,
            "issuanceDate": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "credentialSubject": { "id": holder_did, "address": holder_address, "claims": claims }
        }
        msg_str = json.dumps(credential, sort_keys=True)
        signable_msg = encode_defunct(text=msg_str)
        signed_msg = w3.eth.account.sign_message(signable_msg, private_key=self.private_key_hex)
        return { "payload": credential, "signature": signed_msg.signature.hex() }

    def verify_vc_issuer(self, vc_object):
        try:
            payload = vc_object['payload']
            signature = vc_object['signature']
            issuer_did = payload['issuer']
            msg_str = json.dumps(payload, sort_keys=True)
            signable_msg = encode_defunct(text=msg_str)
            recovered_address = w3.eth.account.recover_message(signable_msg, signature=signature)
            return f"did:eth:{recovered_address}" == issuer_did
        except:
            return False

    def generate_zk_proof(self, challenge_str):
        """Generates Proof. RETURNS HEX STRINGS TO PREVENT JSON CORRUPTION."""
        r = random.randint(1, self.P - 1)
        t = pow(self.G, r, self.P)
        
        challenge_int = int(Web3.keccak(text=challenge_str).hex(), 16)
        c_input = f"{t}{self.zk_public_key}{challenge_int}"
        c = int(Web3.keccak(text=c_input).hex(), 16) % (self.P - 1)
        
        s = (r + c * self.zk_private_key) % (self.P - 1)
        
        return {"t": hex(t), "s": hex(s)}

    def verify_zk_proof(self, prover_identifier, challenge_str, proof):
        """Verifies Proof. HANDLES HEX STRINGS."""
        contract = get_contract(self.contract_address)
        try:
            # --- FIX: LOGIC FOR NEW SECURE CONTRACT ---
            target_address = prover_identifier
            
            # If input is a DID, extract address (did:eth:0x123...)
            if "did:eth:" in prover_identifier:
                target_address = prover_identifier.split(":")[-1]

            # 1. Fetch User Data from Registry Struct
            # Returns: (did, publicKey, exists)
            user_data = contract.functions.registry(target_address).call()
            
            if not user_data[2]: # Check 'exists' boolean
                print(f" ⚠️ Identity {target_address} not found on chain.")
                return False

            # 2. Get Key from Struct (Index 1)
            chain_pub_key_raw = user_data[1]
            public_key = int(chain_pub_key_raw, 16)
            
            # 3. Verify Math
            t = int(proof['t'], 16)
            s = int(proof['s'], 16)
            
            challenge_int = int(Web3.keccak(text=challenge_str).hex(), 16)
            c_input = f"{t}{public_key}{challenge_int}"
            c = int(Web3.keccak(text=c_input).hex(), 16) % (self.P - 1)
            
            left = pow(self.G, s, self.P)
            right = (t * pow(public_key, c, self.P)) % self.P
            
            if left != right:
                print(f"   ❌ Math Mismatch: Data corruption occurred.")
            
            return left == right
        except Exception as e:
            print(f"   ⚠️ Math Error: {e}")
            return False