"""
Docstring for db_test
A small unit to test db.py: make sure to peform tests before using to detect early errors
when used on other machines
"""
import shutil
from db import db

def setup():
    store = db("testdb.lmdb", max_dbs=2)
    return store

def postTest():
    shutil.rmtree("testdb.lmdb")
def TestInsert():
    print("Testing Insert")
    store=setup()
    return store.put("hello", "world")
def TestRetrieval():
    print("Testing Retrieval")
    store = setup()
    if store.get("hello") != b"world":
        print("Unable to retrieve data")
    return "world"

if __name__ =="__main__":
    TestInsert()
    TestRetrieval()
    postTest()
    print("Test Completed successfully")