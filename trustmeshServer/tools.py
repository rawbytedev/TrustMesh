import json
from typing import List, Union
from langchain.tools import tool
import requests
from core import ArcHandler, Storage

# Initialize storage and ArcHandler
BASE = "http://127.0.0.1:8000"
store = Storage()
arc = ArcHandler(
    provider_url="http://127.0.0.1:8545",
    contract_address="0xYourEscrowContract",
    abi=["1"],  # load ABI JSON here
    agent_key="0xYourPrivateKey",
    storage=store
)

@tool("release_funds")
def release_funds_tool(escrow_id: int, reason: str) -> str:
    """Release funds to seller for a given escrow."""
    receipt = arc.Release(escrow_id, reason)
    return f"Released escrow {escrow_id} with reason '{reason}', tx={receipt['transactionHash'].hex()}"

@tool("refund_funds")
def refund_funds_tool(escrow_id: int, reason: str) -> str:
    """Refund buyer for a given escrow."""
    receipt = arc.Refund(escrow_id, reason)
    return f"Refunded escrow {escrow_id} with reason '{reason}', tx={receipt['transactionHash'].hex()}"

@tool("extend_escrow")
def extend_escrow_tool(escrow_id: int, extra_seconds: int, reason: str) -> str:
    """Extend escrow deadline by extra_seconds."""
    receipt = arc.ExtendEscrow(escrow_id, extra_seconds, reason)
    return f"Extended escrow {escrow_id} by {extra_seconds}s, reason '{reason}', tx={receipt['transactionHash'].hex()}"

@tool("finalize_expired_refund")
def finalize_expired_refund_tool(escrow_id: int, reason: str) -> str:
    """Finalize an expired escrow and refund buyer."""
    receipt = arc.FinalizeExpiredRefund(escrow_id, reason)
    return f"Finalized expired escrow {escrow_id}, refunded buyer, reason '{reason}', tx={receipt['transactionHash'].hex()}"



@tool("query_shipment")
def query_shipment(ids: Union[str, List[str]]) -> str:
    """Query shipment details by ID or list of IDs from external service."""
    try:
        res = requests.post(f"{BASE}/query", data=json.dumps(ids))
        if res.status_code == 200:
            return json.dumps(res.json())
        return f"Error {res.status_code}: {res.text}"
    except Exception as e:
        return f"Shipment query failed: {e}"