import asyncio, time, pytest
from core import Cache, EscrowType, TimerScheduler, BatchRunner
import logging

@pytest.mark.asyncio
async def test_cache_add_and_pop():
    c = Cache()
    c.add(1, EscrowType.LINKED)
    c.add(2, EscrowType.EXPIRED)
    batch = c.pop_batch(2)
    assert len(batch) == 2
    assert batch[0].etype == EscrowType.EXPIRED  # priority ordering
import pytest, asyncio, time

def test_cache_add_and_retrieve():
    c = Cache()
    c.add(1, EscrowType.EXPIRED)
    c.add(2, EscrowType.LINKED)
    assert 1 in c._entries
    assert 2 in c._entries
    assert c._entries[1].etype == EscrowType.EXPIRED

def test_cache_pop_batch_respects_priority_and_order():
    c = Cache()
    # Lower enum value = higher priority
    c.add(1, EscrowType.CANCELLED)  # priority 1
    time.sleep(0.01)
    c.add(2, EscrowType.LINKED)     # priority 2
    batch = c.pop_batch(2)
    assert [e.escrow_id for e in batch] == [1, 2]
    assert all(e.locked for e in batch)
    assert all(e.seen_count == 1 for e in batch)

def test_cache_release_removes_entry():
    c = Cache()
    c.add(42, EscrowType.EXPIRED)
    c.release(42)
    assert 42 not in c._entries

@pytest.mark.asyncio
async def test_timer_scheduler():
    t = TimerScheduler()
    results = []
    async def cb(entry): results.append(entry.escrow_id)
    t.set_timer(42, 1, "recheck")
    task = asyncio.create_task(t.run(cb))
    await asyncio.sleep(2)
    assert 42 in results
    task.cancel()

@pytest.mark.asyncio
async def test_timer_scheduler_triggers_callback():
    cbs = []
    async def cb(entry): cbs.append(entry.escrow_id)

    sched = TimerScheduler()
    sched.set_timer(99, delay=1, reason="retry")
    task = asyncio.create_task(sched.run(cb))
    await asyncio.sleep(1.5)
    task.cancel()
    assert cbs == [99]

@pytest.mark.asyncio
async def test_timer_scheduler_orders_multiple():
    order = []
    async def cb(entry): order.append(entry.escrow_id)

    sched = TimerScheduler()
    sched.set_timer(1, delay=1, reason="a")
    sched.set_timer(2, delay=2, reason="b")
    task = asyncio.create_task(sched.run(cb))
    await asyncio.sleep(2.5)
    task.cancel()
    assert order == [1, 2]

@pytest.mark.asyncio
async def test_batch_runner_triggers():
    c = Cache()
    for i in range(5):
        c.add(i, EscrowType.LINKED)
    results = []
    async def fake_ai(batch): results.extend([e.escrow_id for e in batch])
    runner = BatchRunner(c, threshold=5, interval=1)
    task = asyncio.create_task(runner.run(fake_ai))
    await asyncio.sleep(2)
    assert len(results) == 5  # successfully processed batch
    task.cancel()


@pytest.mark.asyncio
async def test_batch_runner_triggers_on_threshold():
    c = Cache()
    results = []
    async def fake_ai(batch): results.extend([e.escrow_id for e in batch])

    runner = BatchRunner(c, threshold=3, interval=10)
    task = asyncio.create_task(runner.run(fake_ai))

    for i in range(3):
        c.add(i, EscrowType.LINKED)

    await asyncio.sleep(1.5)
    task.cancel()
    assert set(results) == {0, 1, 2}

@pytest.mark.asyncio
async def test_batch_runner_triggers_on_interval():
    c = Cache()
    results = []
    async def fake_ai(batch): results.extend([e.escrow_id for e in batch])

    runner = BatchRunner(c, threshold=10, interval=1)
    task = asyncio.create_task(runner.run(fake_ai))

    c.add(42, EscrowType.LINKED)
    await asyncio.sleep(1.5)
    task.cancel()
    assert results == [42]

@pytest.mark.asyncio
async def test_batch_runner_multiple_batches():
    c = Cache()
    results = []
    async def fake_ai(batch): results.append([e.escrow_id for e in batch])

    runner = BatchRunner(c, threshold=2, interval=10)
    task = asyncio.create_task(runner.run(fake_ai))

    c.add(1, EscrowType.LINKED)
    c.add(2, EscrowType.LINKED)
    await asyncio.sleep(1.2)
    c.add(3, EscrowType.CANCELLED)
    c.add(4, EscrowType.EXPIRED)
    await asyncio.sleep(1.2)
    task.cancel()

    # Two separate batches should have been processed
    assert any(1 in b and 2 in b for b in results)
    assert any(3 in b and 4 in b for b in results)

@pytest.mark.asyncio
async def test_batch_runner_stress_many_entries():
    c = Cache()
    results = []
    async def fake_ai(batch): results.extend([e.escrow_id for e in batch])

    runner = BatchRunner(c, threshold=50, interval=5)
    task = asyncio.create_task(runner.run(fake_ai))

    for i in range(100):
        c.add(i, EscrowType.LINKED)

    await asyncio.sleep(3)
    task.cancel()
    # All 100 should eventually be processed
    assert set(results) == set(range(100))

@pytest.mark.asyncio
async def test_batch_runner_respects_escrow_ordering():
    c = Cache()
    # Add escrows with different priorities and slight delays
    c.add(1, EscrowType.LINKED)     # priority 2
    time.sleep(0.01)
    c.add(2, EscrowType.CANCELLED)  # priority 1 (higher)
    time.sleep(0.01)
    c.add(3, EscrowType.EXPIRED)    # priority 0 (highest)

    results = []
    async def fake_ai(batch):
        # Record the order escrows are flushed
        results.extend([e.escrow_id for e in batch])

    runner = BatchRunner(c, threshold=3, interval=1)
    task = asyncio.create_task(runner.run(fake_ai))
    await asyncio.sleep(2)
    task.cancel()

    # Assert that escrows were processed in correct priority order
    assert results == [3, 2, 1]

def test_seen_count_affects_ordering():
    c = Cache()
    c.add(1, EscrowType.LINKED)
    c.add(2, EscrowType.LINKED)
    batch1 = c.pop_batch(1)
    batch2 = c.pop_batch(2)
    # Escrow 1 should now have higher seen_count, so escrow 2 comes first
    assert [e.escrow_id for e in batch2] == [2, 1]
