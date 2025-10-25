import uuid
import hashlib

## needed to make circle API requests
def newuuid() -> uuid.UUID:
    return uuid.uuid4()

def dighash(data:bytes) -> bytes:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).digest()

def hexhash(data:bytes) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()



