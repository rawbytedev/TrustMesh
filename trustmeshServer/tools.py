import json
import logging
import httpx
from pydantic import BaseModel
from langchain.tools import tool
from core import ArcHandler, Storage, TimerScheduler

BASE = "http://127.0.0.1:8000"


def make_tools(arc: ArcHandler, storage: Storage, timer: TimerScheduler):
    # --- Tool functions ---
    @tool("release_funds")
    async def release_funds(escrow_id: int, reason: str) -> str:
        """Release funds to seller for a given escrow."""
        receipt = await arc.Release(escrow_id, reason)
        return f"Released escrow {escrow_id} with reason '{reason}', tx={receipt['transactionHash'].hex()}"

    @tool("refund_funds")
    async def refund_funds(escrow_id: int, reason: str) -> str:
        """Refund buyer for a given escrow."""
        receipt = await arc.Refund(escrow_id, reason)
        return f"Refunded escrow {escrow_id} with reason '{reason}', tx={receipt['transactionHash'].hex()}"

    @tool("extend_escrow")
    async def extend_escrow(escrow_id: int, extra_seconds: int, reason: str) -> str:
        """Extend escrow deadline by extra_seconds."""
        receipt = await arc.ExtendEscrow(escrow_id, extra_seconds, reason)
        return f"Extended escrow {escrow_id} by {extra_seconds}s, reason '{reason}', tx={receipt['transactionHash'].hex()}"

    @tool("finalize_expired_refund")
    async def finalize_expired_refund(escrow_id: int, reason: str) -> str:
        """Finalize an expired escrow and refund buyer."""
        receipt = await arc.FinalizeExpiredRefund(escrow_id, reason)
        return f"Finalized expired escrow {escrow_id}, refunded buyer, reason '{reason}', tx={receipt['transactionHash'].hex()}"

    @tool("query_shipment")
    async def query_shipment(id: str) -> str:
        """Query shipment details by ID from external service."""
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(f"{BASE}/query", data=json.dumps(id))
                if res.status_code == 200:
                    storage.save_shipment_states(id, res.json())
                    return json.dumps(res.json())
                return f"Error {res.status_code}: {res.text}"
        except Exception as e:
            return f"Shipment query failed: {e}"
    
    @tool("set_timer")
    async def set_timer(escrow_id:int, seconds:int, notes:str) -> str:
        "schedules a timer"
        timer.set_timer(escrow_id, seconds, notes)
        return f"Timer set for escrow {escrow_id} in {seconds}s: {notes}"

    @tool("get_escrow_by_id")
    async def get_escrow_by_id(escrow_id: int) -> str:
        """Return the latest state of an Escrow"""
        state = await storage.get_latest(escrow_id)
        if state:
            logging.info(f"Found escrow {escrow_id} in storage")
            return state[1]
        return f"Escrow for {escrow_id} not found"
    
    return [get_escrow_by_id, set_timer, 
            query_shipment, release_funds,
            refund_funds, extend_escrow,
            finalize_expired_refund
            ]