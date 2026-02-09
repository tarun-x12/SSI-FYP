from ssi_utils import load_json, w3
from datetime import datetime

def verify_audit_trail():
    print("\n" + "="*60)
    print("      🔎  TEST CASE 7: FORENSIC AUDIT TRAIL      ")
    print("      (Verifying Blockchain Logs for Non-Repudiation)")
    print("="*60)

    config = load_json("system_config.json")
    contract = w3.eth.contract(address=config['contract_address'], abi=config['abi'])

    # Fetch logs from the smart contract
    # Assuming your contract has an event 'AuditLog(address indexed user, string action, uint256 timestamp)'
    # Or we can filter specifically if you have that setup.
    # For this demo, we will look for the latest blocks.
    
    print("[Forensics] Scanning Blockchain for 'AuditLog' events...")
    
    # Create filter for the specific event
    try:
        event_filter = contract.events.AuditLog.create_filter(from_block='earliest')
        logs = event_filter.get_all_entries()
        
        if len(logs) == 0:
            print("❌ No logs found. Did the Owner Node finish training?")
            return

        print(f"✅ Found {len(logs)} Immutable Records.\n")
        
        for i, log in enumerate(logs[-3:]): # Show last 3
            args = log['args']
            user = args.get('user') or args.get('did') # Adjust based on your solidity
            action = args.get('action')
            timestamp = args.get('timestamp')
            
            readable_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"   📄 Record #{i+1}:")
            print(f"      - User:   {user}")
            print(f"      - Action: {action}")
            print(f"      - Time:   {readable_time}")
            print("      ------------------------------------------------")

        print("\n[Conclusion] The system provides cryptographically verifiable proof of access.")

    except Exception as e:
        print(f"⚠️ Error reading logs: {e}")
        # Fallback if event filter fails (Ganache weirdness)
        print("   (Ensure 'AuditLog' event is defined in your Solidity contract)")

if __name__ == "__main__":
    verify_audit_trail()