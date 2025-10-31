import asyncio
import json
from typing import List, Union
from langchain.tools import tool
import requests
from core import ArcHandler, Storage, BatchRunner, TimerScheduler 

BASE = "http://127.0.0.1:8000"

Arc = ArcHandler("","","","")
store = Storage()
Batch = BatchRunner(store.cache)
timer = TimerScheduler()   


@tool("get_escrow_state", return_direct=True)
def get_escrow_state(self, escrow_id: str) -> str:
    """Get the current state of an escrow by ID."""
    return f"Mock escrow {escrow_id}: status=PENDING, buyer=0x123, seller=0x456"

# Release funds tool
@tool("release_funds")
def release_funds(escrow_id: str, reason: str) -> str:
    """Release funds to seller for a given escrow."""
    return f"Released escrow {escrow_id} with reason: {reason}"

# Refund funds tool
@tool("refund_funds")
def refund_funds(escrow_id: str, reason: str) -> str:
    """Refund buyer for a given escrow."""
    return f"Refunded escrow {escrow_id} with reason: {reason}"

@tool("set_timer")
def set_timer(escrow_id:int,seconds:int, note:str):
    timer.set_timer(escrow_id, seconds,note)

@tool("get_escrow_by_id")
def get_escrow(id:int):
    if isinstance(id, int):
       details = [i for i in store.get_escrow_by_id(id)]
       return details[-1]

"""Shipment related tools and helpers"""
@tool("query_shipment")
def get_shipment_details(id: Union[str, List[str]]):
    result = get_shipment(id)
    return result if result else "None"

def get_shipment(ids: Union[str, List[str]]):
    if gethealth():
        payload = json.dumps(ids)
        res = requests.post(f"{BASE}/query", data=payload)
        if res.status_code == 200:
            return res.json()

def gethealth():
    try:
        res = requests.get(f"{BASE}/health")
        res.raise_for_status()
        payload = res.json()
        return payload.get("status") == "ok"
    except requests.RequestException:
        return False


async def event_listener(cache):
        block = w3.eth.block_number
        while True:
            latest = w3.eth.block_number
            if block <= latest:
                logs = await asyncio.to_thread(
                w3.eth.get_logs,
                {"fromBlock": block, "toBlock": block, "address": self.contract_addr}
            )
                for log in logs:
                    cache.add()
                block += 1
            await asyncio.sleep(1)  # yield control