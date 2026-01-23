from eth_account import Account

# 1. Enable HD Wallet features
Account.enable_unaudited_hdwallet_features()

# 2. PASTE THE SAME MNEMONIC FROM YOUR GANACHE WORKSPACE HERE
GANACHE_MNEMONIC ="group wheat laptop square assault degree kind burden purpose flight learn voice"

def get_ganache_key(index):
    """
    Derives the Private Key for a specific Ganache index.
    Index 0 = GA
    Index 1 = RI
    Index 2 = LG
    ...
    """
    # Standard Ethereum Path: m/44'/60'/0'/0/INDEX
    acct = Account.from_mnemonic(GANACHE_MNEMONIC, account_path=f"m/44'/60'/0'/0/{index}")
    return acct.key.hex()

# Test it immediately
if __name__ == "__main__":
    print(f"Index 0 Key: {get_ganache_key(0)}")
    print(f"Index 1 Key: {get_ganache_key(1)}")


    