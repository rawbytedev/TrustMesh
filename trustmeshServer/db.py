"""
Docstring for db

Local database to store events from smartcontract
We implement the design with caching and direct write to disk
retrieval of information passes throught the cache before hitting the disk that ensure that
for new data retrieval is fast but for older ones we can still reliably retrieve it from disk
storage
"""
from utils import dighash
import lmdb as tool
from collections import OrderedDict

"""
key are referred as follow
for each event a unique prefix
EscrowCreated => ec:
and so on
we'll get [ec:id](hashed using sha256) as key(32 bytes) always constant
but values will be stored as plaintext directly for production use encoder
and decoder for values
"""
CACHESIZE = 30
class DBError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
class DB:
    def __init__(self,path="trustmesh.db", max_dbs=2):
        self.path = path
        self.cache = OrderedDict()
        self.cache_size = CACHESIZE
        self.db= tool.open(path, max_dbs=max_dbs) ## open database

    def _cache_set(self, key, value):
        if len(self.cache) >= self.cache_size:
            self.cache.popitem(last=False)  # evict oldest
        self.cache[key] = value
    
    """
    keys follow the prefix rules
    This should be safe but incase keep check to detect errors from db when read
    """
    def get(self,key):
        if not key:
            raise DBError("Key can't be empty")
        if key in self.cache:
            return self.cache[key]
        with self.db.begin(write=False) as txn:
            val = txn.get(dighash(key))
            if val is None:
                raise DBError(f"Value for key {key} not found")
            decoded = val.decode()
            self._cache_set(key,decoded)
            return decoded
            
    """
    Operation will mostly succeed for production grade adding more checks and handling 
    errors on write will be necessary
    """
    def put(self, key, value):
        if not key:
            raise DBError("Key can't be empty")
        if not value:
            raise DBError("Value can't be empty")
        self._cache_set(key, value)
        try:
            with self.db.begin(write=True) as txn:
                return txn.put(dighash(key), value.encode())
        except:
            return DBError("Can't Insert item into database")
    
    def close(self):
       self.db.close()

