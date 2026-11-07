# Oconnor Burton - 2108222
# Chord DHT with finger-table routing.
#
# This is a single-process simulation: node references represent network links.
# Finger tables are rebuilt after membership changes to keep the implementation
# easy to understand. Lookups use the finger table and take O(log N) hops
# under the usual Chord assumptions.

import hashlib


class Node:
    def __init__(self, name, iden):
        self.name = name
        self.iden = iden
        self.next = None
        self.prev = None

        # hash -> {original_key: value}
        # Buckets allow distinct keys with the same truncated hash.
        self.keys = {}

        # fingerTable[i] is successor((iden + 2**i) mod 2**m)
        self.fingerTable = []

    def addKey(self, key, keyHash, value):
        bucket = self.keys.setdefault(keyHash, {})
        bucket[key] = value

    def removeKey(self, key, keyHash):
        bucket = self.keys.get(keyHash)
        if bucket is None:
            return None

        value = bucket.pop(key, None)
        if not bucket:
            del self.keys[keyHash]
        return value

    def getKey(self, key, keyHash):
        return self.keys.get(keyHash, {}).get(key)


class DataItem:
    def __init__(self, dataId, value):
        self.iden = dataId
        self.value = value
        self.key = None


class ChordNetwork:
    def __init__(self, m=6):
        if m < 1:
            raise ValueError("m must be at least 1")

        self.m = m
        self.ringSize = 2 ** m
        self.nodes = {}  # Node object -> node identifier

    def hashFunction(self, item):
        sha1_hash = hashlib.sha1(str(item).encode("utf-8")).hexdigest()
        return int(sha1_hash, 16) % self.ringSize

    @staticmethod
    def _in_open_interval(value, start, end):
        """Return whether value is in the clockwise interval (start, end)."""
        if start < end:
            return start < value < end
        if start > end:  # interval wraps around zero
            return value > start or value < end
        # Equal endpoints represent the whole ring, excluding the endpoint.
        return value != start

    @staticmethod
    def _in_open_closed_interval(value, start, end):
        """Return whether value is in the clockwise interval (start, end]."""
        if start < end:
            return start < value <= end
        if start > end:  # interval wraps around zero
            return value > start or value <= end
        # A one-node ring owns the entire identifier space.
        return True

    def _linearSuccessor(self, keyHash):
        """Internal O(N) lookup used when building finger tables."""
        if not self.nodes:
            return None

        ordered_nodes = sorted(self.nodes, key=lambda node: node.iden)
        for node in ordered_nodes:
            if keyHash <= node.iden:
                return node
        return ordered_nodes[0]  # wrap around the ring

    def _rebuildRing(self):
        ordered_nodes = sorted(self.nodes, key=lambda node: node.iden)
        count = len(ordered_nodes)

        if count == 0:
            return

        for i, node in enumerate(ordered_nodes):
            node.prev = ordered_nodes[(i - 1) % count]
            node.next = ordered_nodes[(i + 1) % count]

        self._rebuildFingerTables()

    def _rebuildFingerTables(self):
        """Recompute every node's m finger entries after a membership change."""
        for node in self.nodes:
            node.fingerTable = []
            for i in range(self.m):
                start = (node.iden + (2 ** i)) % self.ringSize
                node.fingerTable.append(self._linearSuccessor(start))

    def addNode(self, name):
        nodeHash = self.hashFunction(name)

        # A Chord identifier must be unique in this simulation.
        for existing in self.nodes:
            if existing.iden == nodeHash:
                raise ValueError(
                    f"Node identifier collision: {name!r} and "
                    f"{existing.name!r} both hash to {nodeHash}"
                )

        node = Node(name, nodeHash)
        old_nodes = list(self.nodes)

        self.nodes[node] = nodeHash
        self._rebuildRing()

        # Reassign existing data according to the new ring ownership.
        if old_nodes:
            self._redistributeKeys()

        return node

    def _redistributeKeys(self):
        """Move keys to the node responsible after a membership change."""
        stored_items = []

        for node in list(self.nodes):
            for keyHash, bucket in list(node.keys.items()):
                for key, value in list(bucket.items()):
                    stored_items.append((key, keyHash, value))
            node.keys.clear()

        for key, keyHash, value in stored_items:
            owner = self.findSuccessor(keyHash)
            owner.addKey(key, keyHash, value)

    def removeNode(self, node_or_name):
        target = None

        for node in self.nodes:
            if node is node_or_name or node.name == node_or_name:
                target = node
                break

        if target is None:
            return False

        # Collect data before removing the node.
        stored_items = []
        for keyHash, bucket in target.keys.items():
            for key, value in bucket.items():
                stored_items.append((key, keyHash, value))

        del self.nodes[target]
        target.next = None
        target.prev = None
        target.fingerTable = []

        self._rebuildRing()

        for key, keyHash, value in stored_items:
            owner = self.findSuccessor(keyHash)
            if owner is not None:
                owner.addKey(key, keyHash, value)

        return True

    def findSuccessor(self, keyHash, startNode=None):
        """Find the responsible node using Chord finger-table routing."""
        if not self.nodes:
            return None

        keyHash %= self.ringSize
        current = startNode if startNode in self.nodes else next(iter(self.nodes))

        if len(self.nodes) == 1:
            return current

        # If the key lies between this node and its successor, return successor.
        if self._in_open_closed_interval(keyHash, current.iden, current.next.iden):
            return current.next

        visited = set()

        while current not in visited:
            visited.add(current)

            # Find the closest finger that strictly precedes keyHash.
            next_hop = None
            for finger in reversed(current.fingerTable):
                if finger is not None and self._in_open_interval(
                    finger.iden, current.iden, keyHash
                ):
                    next_hop = finger
                    break

            # The successor is a safe fallback if no useful finger is found.
            if next_hop is None:
                next_hop = current.next

            if next_hop == current:
                return current.next

            current = next_hop

            if self._in_open_closed_interval(
                keyHash, current.iden, current.next.iden
            ):
                return current.next

        # Defensive fallback for malformed/stale routing state.
        return self._linearSuccessor(keyHash)

    def addData(self, dataItem, value):
        keyHash = self.hashFunction(dataItem)
        node = self.findSuccessor(keyHash)

        if node is None:
            raise RuntimeError("Cannot store data: the DHT has no nodes")

        node.addKey(dataItem, keyHash, value)
        return node

    def getData(self, dataItem):
        keyHash = self.hashFunction(dataItem)
        node = self.findSuccessor(keyHash)

        if node is None:
            return None

        return node.getKey(dataItem, keyHash)

    def keyLookUp(self, dataItem):
        """Return the node responsible for a data item's hash."""
        return self.findSuccessor(self.hashFunction(dataItem))

    def printNetwork(self):
        for node in sorted(self.nodes, key=lambda item: item.iden):
            print(
                f"Node {node.name} (ID {node.iden}) | "
                f"prev={node.prev.iden} | next={node.next.iden} | "
                f"keys={node.keys}"
            )
            print(
                "  fingers:",
                [
                    (node.iden + (2 ** i)) % self.ringSize
                    for i in range(self.m)
                ],
                "->",
                [finger.iden for finger in node.fingerTable],
            )


if __name__ == "__main__":
    chord = ChordNetwork(m=6)

    chord.addNode("197:25:01:22")
    chord.addNode("127:100:33:88")
    chord.addNode("15:200:108:10")

    chord.addData("hello.py", "print('Hello World')")
    chord.addData("password.txt", "password123, 121402, iL0veC@s")
    chord.addData("presentation.pdf", "This is my presentation on Distributed hash tables...")

    chord.printNetwork()

    print("\nRetrieval tests:")
    for key in ("hello.py", "password.txt", "presentation.pdf"):
        owner = chord.keyLookUp(key)
        print(f"{key!r} -> node {owner.name} (ID {owner.iden})")
        print(" value:", chord.getData(key))

    print("\nAdding another node and checking data remains available:")
    chord.addNode("10.10.10")
    for key in ("hello.py", "password.txt", "presentation.pdf"):
        print(f"{key!r} -> {chord.getData(key)!r}")

    print("\nRemoving a node and checking data remains available:")
    chord.removeNode("15:200:108:10")
    for key in ("hello.py", "password.txt", "presentation.pdf"):
        print(f"{key!r} -> {chord.getData(key)!r}")
