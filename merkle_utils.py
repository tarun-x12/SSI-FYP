import hashlib

def hash_data(data_str):
    """Standard SHA256 Hash for Merkle Tree"""
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

class MerkleTree:
    def __init__(self, leaves):
        self.leaves = [hash_data(l) for l in leaves]
        self.tree = [self.leaves]
        self._build_tree()

    def _build_tree(self):
        current_level = self.leaves
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                # If odd number of nodes, duplicate the last one
                right = current_level[i+1] if i+1 < len(current_level) else left
                combined = left + right
                next_level.append(hash_data(combined))
            self.tree.append(next_level)
            current_level = next_level

    def get_root(self):
        return self.tree[-1][0] if self.tree else None

    def get_proof(self, leaf_data):
        """Generates the sibling path needed to prove a leaf exists"""
        target_hash = hash_data(leaf_data)
        if target_hash not in self.leaves:
            return None
        
        index = self.leaves.index(target_hash)
        proof = []
        
        for level in self.tree[:-1]: # Skip root layer
            is_right_node = index % 2 == 1
            sibling_index = index - 1 if is_right_node else index + 1
            
            # Handle odd number of leaves case (duplicate last)
            if sibling_index >= len(level):
                sibling_index = index 

            proof.append({
                "sibling": level[sibling_index],
                "direction": "left" if is_right_node else "right" # Sib direction
            })
            index //= 2
            
        return proof

def verify_merkle_proof(leaf_data, proof, root):
    """Reconstructs the root from the leaf + proof and checks against expected root"""
    current_hash = hash_data(leaf_data)
    
    for node in proof:
        sibling = node['sibling']
        if node['direction'] == "right":
            combined = current_hash + sibling
        else:
            combined = sibling + current_hash
        current_hash = hash_data(combined)
        
    return current_hash == root