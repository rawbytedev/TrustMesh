import pytest
from tools import make_tools
from core import ArcHandler, Storage, TimerScheduler

class DummyReceipt():
    def __init__(self, tx="0xabc"):
        self.transactionHash = bytes.fromhex(tx[2:])


class DummyArc(ArcHandler):
    async def Release(self, id, reason) -> dict[str, object]: return {"transactionHash": b"\x12"*32}
    async def Refund(self, id, reason) -> dict[str, object]: return {"transactionHash": b"\x34"*32}
    async def ExtendEscrow(self, id, secs, reason) -> dict[str, object]: return {"transactionHash": b"\x56"*32}
    async def FinalizeExpiredRefund(self, id, reason) -> dict[str, object]: return {"transactionHash": b"\x78"*32}

@pytest.fixture
def Basetool():
    arc = DummyArc()
    storage = Storage()
    timer = TimerScheduler()
    Basetools = {t.name: t for t in make_tools(arc, storage, timer)}
    
    return Basetools

@pytest.mark.asyncio
async def test_release_and_refund_tools(Basetool):
    out = await Basetool["release_funds"].coroutine(1, "ok")
    assert "Released escrow 1" in out
    out = await Basetool["refund_funds"].coroutine(2, "bad")
    assert "Refunded escrow 2" in out
    
@pytest.mark.asyncio
async def test_release_tool(Basetool):
    out = await Basetool["release_funds"].coroutine(1, "ok")
    assert "Released escrow 1" in out

@pytest.mark.asyncio
async def test_refund_tool(Basetool):
    out = await Basetool["refund_funds"].coroutine(2, "buyer issue")
    assert "Refunded escrow 2" in out

@pytest.mark.asyncio
async def test_extend_tool(Basetool):
    out = await Basetool["extend_escrow"].coroutine(3, 3600, "delay")
    assert "Extended escrow 3 by 3600s" in out

@pytest.mark.asyncio
async def test_finalize_tool(Basetool):
    out = await Basetool["finalize_expired_refund"].coroutine(4, "expired")
    assert "Finalized expired escrow 4" in out

"""
def test_query_shipment(monkeypatch, Basetool):
    class DummyResp:
        status_code = 200
        def json(self): return {"id": "SHIP-123", "status": "in-transit"}
    monkeypatch.setattr(Basetool["query_shipment"].func.requests, "post", lambda url, data: DummyResp())
    out = Basetool["query_shipment"].func("SHIP-123")
    assert "SHIP-123" in out
"""