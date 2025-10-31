import uuid
import hashlib

"""Those are small helpers used by other functions or methods"""
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

def encode_id(escrow_id: int) -> str:
    """Convert internal int ID to string for JSON/API."""
    return str(escrow_id)

def decode_id(raw: str | int) -> int:
    """Convert external string/int back to internal int."""
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        return int(raw)
    raise ValueError(f"Unsupported escrow_id type: {type(raw)}")


