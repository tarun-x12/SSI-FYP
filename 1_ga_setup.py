from web3 import Web3
from solcx import compile_standard, install_solc, set_solc_version
import json
from ssi_utils import SSIEntity, save_json, w3
from key_manager import get_ganache_key

# --- GANACHE KEY CONFIGURATION ---
PKEY_GA = get_ganache_key(0)

def deploy_contract(account):
    print("[System] Compiling Smart Contract...")
    
    with open("DIDRegistry.sol", "r") as f:
        contract_source = f.read()
    
    install_solc('0.8.0')
    set_solc_version("0.8.0")
    compiled = compile_standard({
        "language": "Solidity",
        "sources": {"DIDRegistry.sol": {"content": contract_source}},
        "settings": {"outputSelection": {"*": {"*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]}}}
    })
    
    bytecode = compiled['contracts']['DIDRegistry.sol']['DIDRegistry']['evm']['bytecode']['object']
    abi = json.loads(compiled['contracts']['DIDRegistry.sol']['DIDRegistry']['metadata'])['output']['abi']

    DidRegistry = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    print(f"[System] Deploying Contract from {account.address}...")
    
    # 1. Build Transaction
    construct_txn = DidRegistry.constructor().build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 3000000,
        'gasPrice': w3.to_wei('20', 'gwei')
    })
    
    # 2. Sign Transaction
    signed = w3.eth.account.sign_transaction(construct_txn, private_key=account.key)
    
    # 3. Send Raw Transaction (FIXED ATTRIBUTE NAME)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    
    # 4. Wait for Receipt
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    return tx_receipt.contractAddress

# --- EXECUTION ---
GA = SSIEntity("Governance Authority", PKEY_GA)

contract_addr = deploy_contract(GA.account)
GA.contract_address = contract_addr

print(f"[GA] Smart Contract Deployed at: {contract_addr}")

# Register GA
GA.register_on_blockchain()

config = {"contract_address": contract_addr, "ga_address": GA.address, "ga_did": GA.did}
save_json("system_config.json", config)

print("[GA] Setup Complete. Waiting for requests...")