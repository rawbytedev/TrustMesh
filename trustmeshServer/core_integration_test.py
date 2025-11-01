# core_integration_test.py
import asyncio, time, pytest
from core import Cache, EscrowType, TimerScheduler, BatchRunner, Storage
from db import DB

class DummyDB:
    """Minimal fake DB that just stores key/values in memory."""
    def __init__(self):
        self.store = {}
    def put(self, key, value):
        self.store[key] = value
    def get(self, key):
        return self.store.get(key)

@pytest.mark.asyncio
async def test_full_pipeline_lifecycle():
    # Setup
    cache = Cache()
    db = DB()
    storage = Storage(db=db, cache=cache)
    scheduler = TimerScheduler()
    runner_results = []

    async def fake_ai(batch):
        # Record the order of escrows processed by BatchRunner
        runner_results.extend([(e.escrow_id, e.etype.name) for e in batch])

    runner = BatchRunner(cache, threshold=2, interval=1)

    # Step 1: Save events into storage (CREATED doesn't go to cache, LINKED does)
    storage.save_escrow_event(1, EscrowType.CREATED, "created-data")
    storage.save_escrow_event(1, EscrowType.LINKED, "linked-data")
    storage.save_escrow_event(2, EscrowType.EXPIRED, "expired-data")

    # At this point, cache should contain escrows 1 (LINKED) and 2 (EXPIRED)
    assert set(cache._entries.keys()) == {1, 2}

    # Step 2: Run BatchRunner to flush cache to AI
    task_runner = asyncio.create_task(runner.run(fake_ai))
    await asyncio.sleep(2)  # allow runner to trigger
    task_runner.cancel()

    # Both escrows should have been processed and removed
    assert set(cache._entries.keys()) == set()
    # Ordering: EXPIRED (priority 0) before LINKED (priority 2)
    assert runner_results == [(2, "EXPIRED"), (1, "LINKED")]

    # Step 3: Test TimerScheduler reintroduces an escrow
    reintroduced = []
    async def timer_cb(entry):
        # When timer fires, re-add escrow to cache
        cache.add(entry.escrow_id, EscrowType.LINKED)
        reintroduced.append(entry.escrow_id)

    scheduler.set_timer(3, delay=1, reason="retry")
    task_sched = asyncio.create_task(scheduler.run(timer_cb))
    await asyncio.sleep(1.5)
    task_sched.cancel()

    # Escrow 3 should have been reintroduced into cache
    assert 3 in cache._entries
    assert reintroduced == [3]
