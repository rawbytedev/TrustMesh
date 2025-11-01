import pytest
import tools

class DummyReceipt:
    def __init__(self, tx="0xabc"):
        self.transactionHash = bytes.fromhex(tx[2:])

@pytest.fixture(autouse=True)
def patch_arc(monkeypatch):
    monkeypatch.setattr(tools.arc, "Release", lambda eid, reason: DummyReceipt())
    monkeypatch.setattr(tools.arc, "Refund", lambda eid, reason: DummyReceipt())
    monkeypatch.setattr(tools.arc, "ExtendEscrow", lambda eid, secs, reason: DummyReceipt())
    monkeypatch.setattr(tools.arc, "FinalizeExpiredRefund", lambda eid, reason: DummyReceipt())

def test_release_tool():
    out = tools.release_funds_tool(1, "ok")
    assert "Released escrow 1" in out

def test_refund_tool():
    out = tools.refund_funds_tool(2, "buyer issue")
    assert "Refunded escrow 2" in out

def test_extend_tool():
    out = tools.extend_escrow_tool(3, 3600, "delay")
    assert "Extended escrow 3 by 3600s" in out

def test_finalize_tool():
    out = tools.finalize_expired_refund_tool(4, "expired")
    assert "Finalized expired escrow 4" in out

def test_query_shipment(monkeypatch):
    class DummyResp:
        status_code = 200
        def json(self): return {"id": "SHIP-123", "status": "in-transit"}
    monkeypatch.setattr(tools.requests, "post", lambda url, data: DummyResp())
    out = tools.query_shipment("SHIP-123")
    assert "SHIP-123" in out
