"""
Docstring for db_test
A small unit to test db.py: make sure to peform tests before using to detect early errors
when used on other machines
"""

import shutil

from test.test_shutil import Error
from db import db

def setup(num_dbs=2):
    store = db("testdb.lmdb", num_dbs)
    return store

def postTest():
    shutil.rmtree("testdb.lmdb")
    shutil.rmtree("__pycache__")

def TestCorrectInsert():
    store=setup()
    res = store.put("hello", "world")
    if res != True:
        return Error("TestCorrectInsert: Failed")
    print("TestCorrectInsert: Passed")

def TestCorrectRetrieval():
    print("Testing Retrieval")
    key = "hello"
    value = "world"
    store = setup()
    val = store.get(key)
    if val != Error:
        if val != value.encode():
            print(f"TestCorrectRetrieval: Failed Expected {value.encode()} but got {val}")
            return
        print("TestCorrectRetrieval: Passed")
        return    
    return Error("TestCorrectRetrieval: Failed")

if __name__ =="__main__":
    TestCorrectInsert()
    TestCorrectRetrieval()
    postTest()
    print("Test Completed successfully")