import os
import psycopg2
from collections import OrderedDict
from utils import dighash

CACHESIZE = 30

class DBError(Exception):
    pass

class DB:
    def __init__(self, dsn=None):
        """
        dsn: Postgres connection string, e.g. from os.environ["TEST_DATABASE_URL"]
        """
        self.cache = OrderedDict()
        self.cache_size = CACHESIZE
        self.conn = psycopg2.connect(dsn or os.environ["TEST_DATABASE_URL"])
        self.conn.autocommit = True
        self._init_schema()

    def _init_schema(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    hash_key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS kv_index (
                    key TEXT PRIMARY KEY,
                    hash_key TEXT NOT NULL REFERENCES kv_store(hash_key)
                );
            """)

    def _cache_set(self, key, value):
        if len(self.cache) >= self.cache_size:
            self.cache.popitem(last=False)
        self.cache[key] = value

    def get(self, key: str):
        if not key:
            raise DBError("Key can't be empty")
        if key in self.cache:
            return self.cache[key]

        hash_key = dighash(key.encode())
        with self.conn.cursor() as cur:
            cur.execute("SELECT value FROM kv_store WHERE hash_key = %s", (hash_key,))
            row = cur.fetchone()
            if not row:
                raise DBError(f"Value for key {key} not found")
            decoded = row[0]
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
            with self.conn.cursor() as cur:
                # Upsert into kv_store
                cur.execute("""
                    INSERT INTO kv_store (hash_key, value)
                    VALUES (%s, %s)
                    ON CONFLICT (hash_key) DO UPDATE SET value = EXCLUDED.value
                """, (hash_key, value))
                # Upsert into kv_index
                cur.execute("""
                    INSERT INTO kv_index (key, hash_key)
                    VALUES (%s, %s)
                    ON CONFLICT (key) DO UPDATE SET hash_key = EXCLUDED.hash_key
                """, (key, hash_key))
        except Exception as e:
            raise DBError(f"Can't insert item: {e}")

    def iterate(self, prefix: str):
        """
        Iterate over all keys in the index with a given prefix (e.g. 'ec:').
        """
        results = []
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT kv_index.key, kv_store.value
                FROM kv_index
                JOIN kv_store ON kv_index.hash_key = kv_store.hash_key
                WHERE kv_index.key LIKE %s
                ORDER BY kv_index.key
            """, (prefix + '%',))
            for k, v in cur.fetchall():
                results.append((k, v))
        return results

    def close(self):
        self.cache.clear()
        self.conn.close()
