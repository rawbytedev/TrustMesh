"""
Docstring for db_test
A small unit to test db.py: make sure to peform tests before using to detect early errors
when used on other machines
"""
import os
import tempfile
import pytest
from db import DB, DBError

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