import json
import time
import hashlib
from web3 import Web3
from eth_account.messages import encode_defunct
from nizkp_lib import SchnorrNIZKP 

# Connect to Ganache
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))

# Contract Interface
CONTRACT_ABI = '[{"inputs":[{"internalType":"address","name":"_owner","type":"address"}],"name":"getPublicKey","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"string","name":"_did","type":"string"},{"internalType":"string","name":"_pubKey","type":"string"}],"name":"register","outputs":[],"stateMutability":"nonpayable","type":"function"}]'

def get_contract(address):
    return w3.eth.contract(address=address, abi=CONTRACT_ABI)

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def load_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

class SSIEntity:
    def __init__(self, name, private_key_hex, contract_address=None):
        self.name = name
        self.account = w3.eth.account.from_key(private_key_hex)
        self.address = self.account.address
        self.did = f"did:eth:{self.address}"
        self.contract_address = contract_address
        
        # ZKP Setup (Treating private key as secret 'x')
        self.secret_x = int(private_key_hex, 16)
        
        # Derive ZKP Public Key 'y' = g^x mod p
        from nizkp_lib import GENERATOR, PRIME_MODULUS
        self.zk_public_key = pow(GENERATOR, self.secret_x, PRIME_MODULUS)

    def register_on_blockchain(self):
        """Registers DID and the ZK-Public Key on Ganache"""
        contract = get_contract(self.contract_address)
        pub_key_str = hex(self.zk_public_key)
        
        tx = contract.functions.register(self.did, pub_key_str).build_transaction({
            'from': self.address,
            'nonce': w3.eth.get_transaction_count(self.address),
            'gas': 3000000,
            'gasPrice': w3.to_wei('20', 'gwei')
        })
        signed_tx = w3.eth.account.sign_transaction(tx, self.account.key)
        
        # FIXED: Using snake_case .raw_transaction for Web3.py v6+
        w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"[{self.name}] Registered DID & ZK-Key on Blockchain.")

    def issue_credential(self, holder_did, holder_address, claims):
        """Standard VC Issuance (Signed by Issuer)"""
        vc_payload = {
            "issuer": self.did,
            "issuer_address": self.address,
            "holder": holder_did,
            "claims": claims,
            "issuanceDate": time.time()
        }
        msg = encode_defunct(text=json.dumps(vc_payload, sort_keys=True))
        signed_msg = w3.eth.account.sign_message(msg, private_key=self.account.key)
        
        return {
            "payload": vc_payload,
            "signature": signed_msg.signature.hex()
        }

    # --- RESTORED METHOD FOR COMPATIBILITY ---
    def verify_credential(self, vc, expected_issuer_addr=None):
        """
        Verifies standard VC signatures.
        Used by Setup Scripts (RI, LG) and Handshake (Analyst).
        """
        payload = vc['payload']
        signature = vc['signature']
        issuer_addr = payload['issuer_address']

        # 1. Recover Address from Signature
        msg = encode_defunct(text=json.dumps(payload, sort_keys=True))
        recovered = w3.eth.account.recover_message(msg, signature=signature)

        # 2. Check if Recovered Address matches the Claimed Issuer
        if recovered != issuer_addr:
             print(f"[{self.name}] ❌ VC Signature Invalid.")
             return False

        # 3. Optional: Check if we trust this specific issuer
        if expected_issuer_addr and recovered != expected_issuer_addr:
             print(f"[{self.name}] ⚠ VC Valid, but issuer is not who we expected.")
             return False

        # (In a real app, we would also check if Issuer is on Blockchain here)
        return True

    # --- NIZKP METHODS ---
    def generate_zk_proof(self, message):
        """Generates PR (Proof) using NIZKP"""
        print(f"[{self.name}] Generating NIZKP for context: '{message}'...")
        proof = SchnorrNIZKP.generate_proof(self.secret_x, self.zk_public_key, message)
        return proof

    def verify_zk_proof(self, prover_address, message, proof):
        """Verifies PR (Proof) by fetching Prover's Key from Blockchain"""
        contract = get_contract(self.contract_address)
        
        chain_pub_key_hex = contract.functions.getPublicKey(prover_address).call()
        
        if not chain_pub_key_hex:
            print(f"[{self.name}] ❌ ZK Verification Failed: Prover DID not found.")
            return False
            
        prover_pub_key_int = int(chain_pub_key_hex, 16)
        is_valid = SchnorrNIZKP.verify_proof(prover_pub_key_int, message, proof)
        
        if is_valid:
            print(f"[{self.name}] ✅ NIZKP Valid! Identity confirmed without revealing keys.")
            return True
        else:
            print(f"[{self.name}] ❌ NIZKP Invalid. Math check failed.")
            return False
    
    # Alias for scripts that might use the newer name
    def verify_vc_issuer(self, vc):
        return self.verify_credential(vc)