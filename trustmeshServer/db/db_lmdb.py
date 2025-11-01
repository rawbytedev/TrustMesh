import lmdb as tool
from collections import OrderedDict
from utils import dighash

CACHESIZE = 30

class DBError(Exception):
    pass

class DB:
    def __init__(self, path="trustmesh.db", index_path="trustmesh_index.db", max_dbs=2):
        self.cache = OrderedDict()
        self.cache_size = CACHESIZE
        self.db = tool.open(path, max_dbs=max_dbs)
        self.index = tool.open(index_path, max_dbs=max_dbs)

    def _cache_set(self, key, value):
        if len(self.cache) >= self.cache_size:
            self.cache.popitem(last=False)
        self.cache[key] = value

    def get(self, key: str):
        if not key:
            raise DBError("Key can't be empty")
        if key in self.cache:
            return self.cache[key]
        with self.db.begin(write=False) as txn:
            hash_key = dighash(key.encode())
            val = txn.get(hash_key)
            if val is None:
                raise DBError(f"Value for key {key} not found")
            decoded = val.decode()
            self._cache_set(key, decoded)
            return decoded

    def put(self, key: str, value: str):
        if not key:
            raise DBError("Key can't be empty")
        if not value:
            raise DBError("Value can't be empty")
        self._cache_set(key, value)
        hash_key = dighash(key.encode())
        try:
            with self.db.begin(write=True) as txn:
                txn.put(hash_key, value.encode())
            with self.index.begin(write=True) as txn:
                txn.put(key.encode(), hash_key)
        except Exception as e:
            raise DBError(f"Can't insert item: {e}")

    def iterate(self, prefix: str):
        """
        Iterate over all keys in the index database with a given prefix (e.g. 'ec:').

        Returns:
            prefix_bytes = prefix.encode()  # LMDB keys must be bytes, so encode the prefix
        """
        results = []
        with self.index.begin(write=False) as txn:
            cursor = txn.cursor()
            prefix_bytes = prefix.encode()
            if cursor.set_range(prefix_bytes):
                with self.db.begin(write=False) as dtxn:
                    # iterate from the current cursor position and stop when keys no longer match the prefix
                    for k, v in cursor:
                        if not k.startswith(prefix_bytes):
                            break
                        # v is the hash_key, fetch from main DB
                        val = dtxn.get(v)
                        if val:
                            # Decode key and value before appending for clarity
                            decoded_key = k.decode()
                            decoded_val = val.decode()
                            results.append((decoded_key, decoded_val))
        return results

    def close(self):
        self.cache.clear()
        self.db.close()
        self.index.close()
