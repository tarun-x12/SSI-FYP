import hashlib
import secrets

# --- NIZKP CONSTANTS (Schnorr Group) ---
# In a real production system, use standard curves like secp256k1 or Curve25519.
# For this implementation, we use a Safe Prime group for clear, readable ZK math.
# (RFC 3526 - 2048 bit MODP Group ID 14 simplified for simulation speed)
PRIME_MODULUS = int('FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1'
                    '29024E088A67CC74020BBEA63B139B22514A08798E3404DD'
                    'EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245'
                    'E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED'
                    'EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D'
                    'C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F'
                    '83655D23DCA3AD961C62F356208552BB9ED529077096966D'
                    '670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B'
                    'E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9'
                    'DE2BCBF6955817183995497CEA956AE515D2261898FA0510'
                    '15728E5A8AACAA68FFFFFFFFFFFFFFFF', 16)
GENERATOR = 2

class SchnorrNIZKP:
    """
    Implements Non-Interactive Zero-Knowledge Proof (NIZKP)
    Protocol: Schnorr Identification with Fiat-Shamir Transform
    """

    @staticmethod
    def generate_proof(private_key_int, public_key_int, message):
        """
        Prover generates a proof: (Commitment, Response)
        Proves knowledge of 'x' in y = g^x without revealing 'x'.
        """
        # 1. Commitment: r = random, t = g^r
        r = secrets.randbelow(PRIME_MODULUS - 1)
        t = pow(GENERATOR, r, PRIME_MODULUS)

        # 2. Challenge: c = H(g, y, t, message) (Fiat-Shamir)
        # We bind the proof to a specific message (e.g., connection request ID)
        challenge_input = f"{GENERATOR}{public_key_int}{t}{message}"
        c = int(hashlib.sha256(challenge_input.encode()).hexdigest(), 16)

        # 3. Response: s = r + c * x
        # Note: We compute modulo (PRIME_MODULUS - 1) for the exponent
        s = (r + c * private_key_int) % (PRIME_MODULUS - 1)

        return {
            "t": hex(t),
            "s": hex(s),
            "c": hex(c) # Included for easier debugging, but Verifier recalculates it
        }

    @staticmethod
    def verify_proof(public_key_int, message, proof):
        """
        Verifier checks the proof.
        Equation: g^s == t * y^c
        """
        t = int(proof['t'], 16)
        s = int(proof['s'], 16)
        
        # 1. Recompute Challenge: c = H(g, y, t, message)
        challenge_input = f"{GENERATOR}{public_key_int}{t}{message}"
        c_recalc = int(hashlib.sha256(challenge_input.encode()).hexdigest(), 16)

        # 2. Verify Equation
        # Left Hand Side: g^s
        lhs = pow(GENERATOR, s, PRIME_MODULUS)
        
        # Right Hand Side: t * y^c
        rhs = (t * pow(public_key_int, c_recalc, PRIME_MODULUS)) % PRIME_MODULUS

        return lhs == rhs