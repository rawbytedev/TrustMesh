import json
import logging
import asyncio, heapq, time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
from web3 import Web3
from db import DB


class EscrowType(Enum):
    # Lower value = higher AI priority (EXPIRED highest)
    EXPIRED = 0
    CANCELLED = 1
    LINKED = 2
    EXTENDED = 3
    ## those doesn't need AI attention
    CREATED = 4
    REFUNDED = 5 # terminal
    RELEASED = 6 # terminal

@dataclass(order=True)
class EscrowRef:
    sort_index: tuple[int, int,float] = field(init=False, repr=False)
    escrow_id: int
    etype: EscrowType
    first_seen_at: float
    last_seen_at: float
    seen_count: int = 0
    locked: bool = False

    def __post_init__(self):
        # Priority: type first, then oldest timestamp
        self.sort_index = (self.etype.value, self.seen_count,self.first_seen_at)
    
    
    def refresh_index(self):
        self.sort_index = (self.etype.value, self.seen_count,self.first_seen_at)
class Cache:
    """Holds references to escrows needing AI attention."""
    logging.info("Cache started")
    def __init__(self):
        self._entries: Dict[int, EscrowRef] = {}
        self._lock = asyncio.Lock()

    async def add(self, escrow_id: int, etype: EscrowType):
        logging.info(f"CACHE: adding {escrow_id}:{etype}")
        async with self._lock:
            if escrow_id not in self._entries:
                now = time.time()
                self._entries[escrow_id] = EscrowRef(
                    escrow_id=escrow_id,
                    etype=etype,
                    first_seen_at=now,
                    last_seen_at=now
                )

    async def pop_batch(self, size: int) -> List[EscrowRef]:
        """
        Selects a batch of escrows for processing, marking them as locked, but does NOT remove them from the cache.
        Caller is responsible for releasing (removing) them after processing.
        """
        async with self._lock:
            batch = sorted(self._entries.values())[:size]
            for e in batch:
                e.locked = True
                e.seen_count += 1
                e.last_seen_at = time.time()
                e.refresh_index() ## needed to update sort_index
            return batch

    async def release(self, escrow_id: int):
        """Release (remove) an escrow from the cache."""
        logging.info(f"CACHE: releasing {escrow_id} ")
        async with self._lock:
            self._entries.pop(escrow_id, None)

    def clear(self):
        """Clear all entries."""
        self._entries.clear()


@dataclass(order=True)
class TimerEntry:
    due_at: float
    escrow_id: int
    reason: str
    attempt: int = 1

class TimerScheduler:
    """Schedules deferred re-checks."""
    def __init__(self):
        self._heap: List[TimerEntry] = []
        self._stop = False

    def stop(self):
        self._stop = True
    def set_timer(self, escrow_id: int, delay: int, reason: str):
        logging.info(f"TIMER: setting timer {escrow_id} delay: {delay}, reason:{reason}")
        entry = TimerEntry(due_at=time.time() + delay, escrow_id=escrow_id, reason=reason)
        heapq.heappush(self._heap, entry)

    async def run(self, callback):
        while not self._stop:
            if not self._heap:
                await asyncio.sleep(0.5)
                continue
            entry = self._heap[0]
            delay = max(0, entry.due_at - time.time())
            if delay == 0:
                heapq.heappop(self._heap)
                await callback(entry)
            else:
                await asyncio.sleep(min(delay,2))

class BatchRunner:
    """Flushes cache to AI when threshold or time window reached."""
    def __init__(self, cache: Cache, threshold: int = 5, interval: int = 5):
        self.cache = cache
        self.threshold = threshold
        self.interval = interval
        self._last_run = time.time()
        
    async def run(self, ai_callback):
        while True:
            now = time.time()
            should_trigger = (
            len(self.cache._entries) >= self.threshold
            or (now - self._last_run) >= self.interval
        )
            if should_trigger:
                # Decide how many to take
                size = self.threshold if len(self.cache._entries) >= self.threshold else len(self.cache._entries)
                logging.info(f"BatchRunner: Processing {size} escrowsS")
                batch = await self.cache.pop_batch(size)
                if batch:
                    try:
                        logging.info("BatchRunner: Waiting for Ai")
                        await ai_callback(batch)
                        for e in batch:
                            await self.cache.release(e.escrow_id)
                    except Exception as e:
                        logging.error(f"BatchRunner: error: {e}")
                        for e in batch:
                            e.locked = False
                self._last_run = now

            await asyncio.sleep(1)

class Storage:
    """Handles persistent and cache storage of escrow data."""
    def __init__(self, db:DB=None, cache:Cache=None):
        self.db = db if db else DB()
        self.cache = cache if cache else Cache()
        self.states = ["ec","lk","ex","cn","xp","rf","rl"]  # escrow states prefixes
    async def save_escrow_event(self, escrow_id: int, type:EscrowType,event_data: str):
        """Save escrow event data based on type.
        CREATED events are stored but not added to cache.
        LINKED, EXTENDED, CANCELLED, EXPIRED events are added to cache for AI processing.
        REFUNDED and RELEASED events are stored but not added to cache. they don't need AI attention. and represent final states.
        """
        if type in (EscrowType.REFUNDED, EscrowType.RELEASED, EscrowType.CREATED):
            logging.info(f"Storage: saving {type}:{escrow_id}")
            self.db.put(f"{self._prefix(type)}:{escrow_id}", event_data)
            return
        # Only non-terminal events go to cache
        logging.info(f"Storage: saving terminal {type}:{escrow_id}")
        key = f"{self._prefix(type)}:{escrow_id}"
        self.db.put(key, event_data)
        await self.cache.add(escrow_id, type)

    def get_escrow_by_id(self, escrow_id: int) -> Dict[str, str]:
        """Retrieve escrow data by checking all possible states."""
        logging.info(f"Retrieving escrow states: {escrow_id}")
        keys = [f"{state}:{escrow_id}" for state in self.states]
        result = {}
        for key in keys:
            try:
                tmp = self.db.get(key)
                if tmp is not None:
                    result[key] = tmp
            except Exception:
                pass
        return result
    
    async def get_latest(self, escrow_id: int) -> Optional[tuple[str, str]]:
        logging.info(f"Retrieving latest states: {escrow_id}")
        data = self.get_escrow_by_id(escrow_id)
        if not data:
            return None
        # Order by prefixes from last state to first
        order = ["rf", "rl","xp","ex","lk","cn","ec"]
        for p in order:
            key = f"{p}:{escrow_id}"
            if key in data:
                return (p, data[key])
        return None
    def save_shipment_states(self, ids, details):
        self.db.put(f"ship:{ids}", details["details"])

    def get_shipment_state(self, ids):
        return self.db.get(f"ship:{ids}")
        
    def _prefix(self, t: EscrowType) -> str:
        return {
        EscrowType.CREATED: "ec",
        EscrowType.LINKED: "lk",
        EscrowType.EXTENDED: "ex",
        EscrowType.CANCELLED: "cn",
        EscrowType.EXPIRED: "xp",
        EscrowType.REFUNDED: "rf",
        EscrowType.RELEASED: "rl",
        }[t]

class ArcHandler:
    """Handle all interaction with Arc Blockchain"""
    def __init__(self, provider_url:str=None, contract_address=None, abi:List[str]=None, agent_key:str=None, storage:Storage=None):
        self.w3 = Web3(Web3.HTTPProvider(provider_url)) if provider_url else None
        self.contract = self.w3.eth.contract(address=contract_address, abi=abi) if contract_address else None
        self.agent = self.w3.eth.account.from_key(agent_key) if agent_key else None
        self.storage:Storage = storage  if storage else Storage()

    async def listen_events(self, from_block: Optional[int]=None):
        """Listen to all escrow events and push into storage/cache."""
        logging.info("ArcHandler: Started Event listener")
        start = from_block or self.w3.eth.block_number
        while True:
            latest = self.w3.eth.block_number
            if latest >= start:
                logs = self.w3.eth.get_logs({"fromBlock": start, "toBlock": latest, "address": self.contract.address})
                logging.info("ArcHandler: captured event logs")
                for log in logs:
                    try:
                        decoded = self._decode_log(log)
                        if decoded:
                            
                            await self.handle_event(decoded)
                    except Exception as e:
                        logging.error(f"Decode error: {e}")
                start = latest + 1
            await asyncio.sleep(2)


    def _decode_log(self, log):
        for ev in [
        self.contract.events.EscrowCreated,
        self.contract.events.ShipmentLinked,
        self.contract.events.FundsReleased,
        self.contract.events.FundsRefunded,
        self.contract.events.EscrowExtended,
        self.contract.events.EscrowExpired,
        self.contract.events.EscrowCancelled,
    ]:
            try:
                return ev().process_log(log)
            except Exception:
                continue
        return None
    
    async def handle_event(self, event):
        """Decode and persist event"""
        logging.info("ArcHandler: Started Processing Event")
        try:
            escrow_id = event["args"]["escrowId"]
            etype = event["event"]  # e.g. "EscrowCreated"
            data = dict(event["args"])
            logging.info(f"Event {etype} for escrow {escrow_id}")
            # Map event name → EscrowType
            from core import EscrowType
            mapping = {
                "EscrowCreated": EscrowType.CREATED,
                "ShipmentLinked": EscrowType.LINKED,
                "EscrowExtended": EscrowType.EXTENDED,
                "EscrowCancelled": EscrowType.CANCELLED,
                "EscrowExpired": EscrowType.EXPIRED,
                "FundsRefunded": EscrowType.REFUNDED,
                "FundsReleased": EscrowType.RELEASED,
            }

            if etype in mapping:
                await self.storage.save_escrow_event(escrow_id=escrow_id,type= mapping[etype], event_data=json.dumps(data))
        except Exception as e:
            logging.error(f"Error handling event: {e}")
    
    ## unused
    def GetEscrows(self):
        """Call contract view to fetch active escrows"""
        try:
            return self.contract.functions.getActiveEscrows().call()
        except Exception as e:
            logging.error(f"Error fetching escrows: {e}")
            return []
##
    def _send_tx(self, fn, *args):
        """Helper to sign and send a transaction"""
        tx = fn(*args).build_transaction({
            "from": self.agent.address,
            "nonce": self.w3.eth.get_transaction_count(self.agent.address),
            "gas": 500000,
            "gasPrice": self.w3.to_wei("5", "gwei"),
        })
        signed = self.agent.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return dict(receipt)

    async def Release(self, id, reason:str):
        """add query shipment"""
        return await asyncio.to_thread(self._send_tx, self.contract.functions.releaseFunds, id, reason)

    async def Refund(self, id, reason:str):
        return await asyncio.to_thread(self._send_tx, self.contract.functions.refund, id, reason)

    async def ExtendEscrow(self, id, secs, reason:str):
        return await asyncio.to_thread(self._send_tx, self.contract.functions.extendEscrow, id, secs, reason)

    async def FinalizeExpiredRefund(self, id, reason:str):
        return await asyncio.to_thread(self._send_tx, self.contract.functions.finalizeExpiredRefund, id, reason)
    
    async def _check_shipment(self, id):
        """Peform a additionnal check to ensure that shipment was indeed delivered"""
        val = await self.storage.get_latest(id) ## the latest should either be LINKED or EXTENDED
        if val:
            valdict = json.loads(val[1])
            return valdict["shipmentId"]