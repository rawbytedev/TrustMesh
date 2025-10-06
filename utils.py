import uuid
import hashlib

## needed to make circle API requests
def newuuid():
    return uuid.uuid4()

def dighash(data:bytes):
    if type(data) != bytes:
        data = data.encode()
    return hashlib.new("sha256", data).digest()

def hexhash(data:bytes):
    if type(data) != bytes:
        data = data.encode()
    return hashlib.new("sha256", data).hexdigest()



