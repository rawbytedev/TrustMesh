"""
Contains the list of tools available and used by Ai to perform actions
"""

"""
Handle request of data feed related to shipment of products
will be plugged into realworld shipment feedback systems in future
Needed by Ai
"""
import asyncio
from typing import List, Union

from web3.auto import w3
from db import DB
from langchain.tools import tool

## only query feed server for shipment details
class FeedCall:
    def __init__(self, url):
        self.url = url
        pass
    
    def get(self, id):
        ## call using api
        pass
"""
Handle all agent interaction with Arc
this include; smart contract registration(must be called once)
wallet generation, peforming smart contract calls
needed by Ai
DB already has a cache so we only needs it
"""


Arc = ArcHandler("","","","")    
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
def set_timer(seconds, note:str):
    pass

@tool("query_shipment")
def get_shipment_details(ids):
    pass

@tool("get_escrow_by_id")
def get_escrow(id: Union[str, List[str]]):
    if isinstance(id, str):
        pass

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