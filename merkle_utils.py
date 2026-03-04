import hashlib


def hash_data(data_str):
    """Generate SHA256 hash"""
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()


class MerkleTree:

    def __init__(self, leaves):

        if not leaves:
            raise ValueError("Merkle tree requires at least one leaf")

        self.leaves = [hash_data(l) for l in leaves]

        self.tree = [self.leaves]

        self._build_tree()


    def _build_tree(self):

        current_level = self.leaves

        while len(current_level) > 1:

            next_level = []

            for i in range(0, len(current_level), 2):

                left = current_level[i]

                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                else:
                    right = left  # duplicate last node

                combined = left + right

                next_level.append(hash_data(combined))

            self.tree.append(next_level)

            current_level = next_level


    def get_root(self):

        if not self.tree:
            return None

        return self.tree[-1][0]


    def get_proof(self, leaf_data):

        """Return sibling path for verification"""

        target_hash = hash_data(leaf_data)

        if target_hash not in self.leaves:
            return None

        index = self.leaves.index(target_hash)

        proof = []

        for level in self.tree[:-1]:

            is_right = index % 2 == 1

            sibling_index = index - 1 if is_right else index + 1

            if sibling_index >= len(level):
                sibling_index = index

            proof.append({
                "sibling": level[sibling_index],
                "direction": "left" if is_right else "right"
            })

            index = index // 2

        return proof


def verify_merkle_proof(leaf_data, proof, root):

    """Verify a leaf using Merkle proof"""

    if proof is None:
        return False

    current_hash = hash_data(leaf_data)

    for node in proof:

        if "sibling" not in node or "direction" not in node:
            return False

        sibling = node["sibling"]

        if node["direction"] == "right":
            combined = current_hash + sibling
        else:
            combined = sibling + current_hash

        current_hash = hash_data(combined)

    return current_hash == root