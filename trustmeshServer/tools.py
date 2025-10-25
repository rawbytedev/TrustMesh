"""
Contains the list of tools available and used by Ai to perform actions
"""

"""
Handle request of data feed related to shipment of products
will be plugged into realworld shipment feedback systems in future
Needed by Ai
"""
import asyncio
from db import DB
from langchain.tools import tool


class FeedCall:
    def __init__(self, path:str="feedbackstores.db", maxdbs:int=2):
        self.store = DB(path, maxdbs)
        self.cache  = {"id":{""}}
        pass
    ## try to get feed dfrom cache
    ## then if not present call updates()
    ## then try again if still not present return not Found
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
class ArcHandler:
    ## handler = ArcHandler(providerurl, contractaddress, abi, agent_key)
    ## asyncio.createtask(handler.listenevents())
    def init(self, provider_url, contract_address, abi, agent_key):
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
        self.contract = self.w3.eth.contract(address=contract_address, abi=abi)
        self.agent = self.w3.eth.account.fromkey(agent_key)

    async def listen_events(self):
        eventfilter = self.contract.events.EscrowCreated.createfilter(fromBlock="latest")
        while True:
            for event in eventfilter.getnew_entries():
                self.handle_event(event)
            await asyncio.sleep(2)
            

    def handle_event(self, event):
        # Store locally (DB, file, memory)
        pass

    ## Obtain all Escrows on smartContract (active ones) // note: storage
    def GetEscrows(self):
        pass

    ## release funds to seller
    def Release(self, id, reason:str):
        pass

    ## refund buyer
    def Refund(self, id, reason:str):
        pass

    def ExtendEscrow(self, id, time, reason:str):
        pass

    def FinalizeExpiredRefund(self, id, reason:str):
        pass

    
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
if __name__ == "__main__":
    feed = FeedCall()
    
    feed.get("1")
    feed.get("aren")