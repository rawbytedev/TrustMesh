import asyncio, heapq, time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
from web3 import Web3
from db import DB


class EscrowType(Enum):
    EXPIRED = 0
    CANCELLED = 1
    LINKED = 2
    EXTENDED = 3
    ## those doesn't need AI attention
    CREATED = 4
    REFUNDED = 5
    RELEASED = 6

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

class Cache:
    """Holds references to escrows needing AI attention."""
    def __init__(self):
        self._entries: Dict[int, EscrowRef] = {}

    def add(self, escrow_id: int, etype: EscrowType):
        if escrow_id not in self._entries:
            now = time.time()
            self._entries[escrow_id] = EscrowRef(
                escrow_id=escrow_id,
                etype=etype,
                first_seen_at=now,
                last_seen_at=now
            )

    def pop_batch(self, size: int) -> List[EscrowRef]:
        """
        Selects a batch of escrows for processing, marking them as locked, but does NOT remove them from the cache.
        Caller is responsible for releasing (removing) them after processing.
        """
        entries = sorted(self._entries.values())
        batch = entries[:size]
        for e in batch:
            e.locked = True
            e.seen_count += 1
            e.last_seen_at = time.time()
        return batch

    def release(self, escrow_id: int):
        """Release (remove) an escrow from the cache."""
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

    def set_timer(self, escrow_id: int, delay: int, reason: str):
        entry = TimerEntry(due_at=time.time() + delay, escrow_id=escrow_id, reason=reason)
        heapq.heappush(self._heap, entry)

    async def run(self, callback):
        while True:
            if not self._heap:
                await asyncio.sleep(1)
                continue
            entry = self._heap[0]
            now = time.time()
            if now >= entry.due_at:
                heapq.heappop(self._heap)
                await callback(entry)
            else:
                await asyncio.sleep(entry.due_at - now)

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
                batch = self.cache.pop_batch(size)
                if batch:
                    try:
                        await ai_callback(batch)
                        for e in batch:
                            self.cache.release(e.escrow_id)
                    except Exception as e:
                        print(f"Error processing batch: {e}")
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
    def save_escrow_event(self, escrow_id: int, type:EscrowType,event_data: str):
        """Save escrow event data based on type.
        CREATED events are stored but not added to cache.
        LINKED, EXTENDED, CANCELLED, EXPIRED events are added to cache for AI processing.
        REFUNDED and RELEASED events are stored but not added to cache. they don't need AI attention. and represent final states.
        """
        if EscrowType(type) == EscrowType.CREATED:
            self.db.put(f"ec:{escrow_id}", event_data)
        if EscrowType(type) == EscrowType.LINKED:
            key = f"lk:{escrow_id}"
            self.db.put(key, event_data)
            self.cache.add(escrow_id, EscrowType.LINKED)
        if EscrowType(type) == EscrowType.EXTENDED:
            key = f"ex:{escrow_id}"
            self.db.put(key, event_data)
            self.cache.add(escrow_id, EscrowType.EXTENDED)
        if EscrowType(type) == EscrowType.CANCELLED:
            key = f"cn:{escrow_id}"
            self.db.put(key, event_data)
            self.cache.add(escrow_id, EscrowType.CANCELLED)
        if EscrowType(type) == EscrowType.EXPIRED:
            key = f"xp:{escrow_id}"
            self.db.put(key, event_data)
            self.cache.add(escrow_id, EscrowType.EXPIRED)
        if EscrowType(type) == EscrowType.REFUNDED:
            key = f"rf:{escrow_id}"
            self.db.put(key, event_data)
        if EscrowType(type) == EscrowType.RELEASED:
            key = f"rl:{escrow_id}"
            self.db.put(key, event_data)


    def get_escrow_by_id(self, escrow_id: int) -> Dict[str, str]:
        """Retrieve escrow data by checking all possible states."""
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

class ArcHandler:
    """Handle all interaction with Arc Blockchain"""
    def __init__(self, provider_url:str, contract_address, abi:str, agent_key:str):
        """Initialize an instance of arc handler with storage and cache"""
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
        self.contract = self.w3.eth.contract(address=contract_address, abi=abi)
        self.agent = self.w3.eth.account.from_key(agent_key)
        

    async def listen_events(self):
        """Listen to event from smart contract on Arc then add them to cache and storage"""
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