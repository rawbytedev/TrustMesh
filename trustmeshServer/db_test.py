"""
Docstring for db_test
A small unit to test db.py: make sure to peform tests before using to detect early errors
when used on other machines
"""
import os
import tempfile
import pytest
from db import DB, DBError
from core import EscrowType, Storage

@pytest.fixture
def temp_db():
    # Create a temporary directory for LMDB
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DB(path=os.path.join(tmpdir, "testdb"))
        yield db
        db.close()

def test_put_and_get(temp_db):
    temp_db.put("key1", "value1")
    assert temp_db.get("key1") == "value1"

def test_get_populates_cache(temp_db):
    temp_db.put("key2", "value2")
    # Clear cache manually to force LMDB read
    temp_db.cache.clear()
    val = temp_db.get("key2")
    assert val == "value2"
    # Now it should also be back in cache
    assert "key2" in temp_db.cache

def test_empty_key_raises(temp_db):
    with pytest.raises(DBError):
        temp_db.put("", "value")
    with pytest.raises(DBError):
        temp_db.get("")

def test_empty_value_raises(temp_db):
    with pytest.raises(DBError):
        temp_db.put("key", "")

def test_missing_key_raises(temp_db):
    with pytest.raises(DBError):
        temp_db.get("does_not_exist")

def test_cache_eviction(temp_db):
    # Small cache for testing
    temp_db.cache_size = 2
    temp_db.put("a", "1")
    temp_db.put("b", "2")
    temp_db.put("c", "3")
    # Oldest ("a") should be evicted
    assert "a" not in temp_db.cache
    assert "b" in temp_db.cache
    assert "c" in temp_db.cache

def test_iterate_returns_only_prefixed_keys(temp_db):
    # Insert some keys with prefix "ec:" and some without
    temp_db.put("ec:1", "value1")
    temp_db.put("ec:2", "value2")
    temp_db.put("ec:3", "value3")
    temp_db.put("other:1", "othervalue")

    results = temp_db.iterate("ec:")

    # Convert to dict for easier assertions
    result_dict = dict(results)

    assert "ec:1" in result_dict
    assert "ec:2" in result_dict
    assert "ec:3" in result_dict
    assert "other:1" not in result_dict

    # Check values match
    assert result_dict["ec:1"] == "value1"
    assert result_dict["ec:2"] == "value2"
    assert result_dict["ec:3"] == "value3"

def test_iterate_empty_prefix_returns_all(temp_db):
    temp_db.put("a:1", "foo")
    temp_db.put("b:1", "bar")

    results = temp_db.iterate("")  # should return everything
    keys = [k for k, _ in results]

    assert "a:1" in keys
    assert "b:1" in keys

class DummyDB(DB):
    def __init__(self):
        self.store = {}
    def put(self, key, value):
        self.store[key] = value
    def get(self, key):
        return self.store.get(key)

def test_get_latest_returns_correct_state():
    db = DummyDB()
    storage = Storage(db=db)

    # Insert CREATED and then REFUNDED
    storage.save_escrow_event(1, EscrowType.CREATED, "created-data")
    storage.save_escrow_event(1, EscrowType.REFUNDED, "refunded-data")

    latest = storage.get_latest(1)
    assert latest[0] == "rf"
    assert latest[1] == "refunded-data"

def test_get_latest_none_if_no_data():
    db = DummyDB()
    storage = Storage(db=db)
    assert storage.get_latest(99) is None

def test_save_shipment():
    ships ={
        "details":[{
            "Shipid":"ship-12",
            "state":"transit"
        }]
    }
    db =DummyDB()
    store = Storage(db)
    store.save_shipment_states("ship-12",ships)
    assert store.get_shipment_state("ship-12") == ships["details"]