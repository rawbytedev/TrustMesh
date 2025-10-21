"""
Docstring for db

Local database to store events from smartcontract
We implement the design with caching and direct write to disk
retrieval of information passes throught the cache before hitting the disk that ensure that
for new data retrieval is fast but for older ones we can still reliably retrieve it from disk
storage
"""
from csv import Error
from utils import dighash
import lmdb as tool

"""
key are referred as follow
for each event a unique prefix
EscrowCreated => ec:
and so on
we'll get [ec:id](hashed using sha256) as key(32 bytes) always constant
but values will be stored as plaintext directly for production use encoder
and decoder for values
"""
class db:
    def __init__(self,path="trustmesh.db", max_dbs=2):
        self.path = path
        self.cache = {} ## note cache needs a limit size implement later
        self.db= tool.open(path, max_dbs=max_dbs) ## open database
    
    """
    keys follow the prefix rules
    This should be safe but incase keep check to detect errors from db when read
    """
    def get(self,key):
        if key == "":
            return Error("Key can't be empty")
        try:
            res = self.cache[key]
            return res
        except KeyError:
            with self.db.begin(write=False) as txn:
                val = txn.get(dighash(key))
                if val == None:
                    return Error("dbError: Value can't be found in Database")
                return val
    """
    Operation will mostly succeed for production grade adding more checks and handling 
    errors on write will be necessary
    """
    def put(self, key, value):
        if key == "":
            return Error("Key can't be empty")
        if value == "":
            return Error("Value can't be empty")
        try:
            self.cache[key] = value
            with self.db.begin(write=True) as txn:
                return txn.put(dighash(key), value.encode())
        except:
            return Error("Can't Insert item into database")

