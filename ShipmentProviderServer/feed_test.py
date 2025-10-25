import json
import time
from typing import Dict
import requests
import pytest

BASE = "http://127.0.0.1:8000"



def test_add_and_query():
    data = {"id": "X1", "status": "created", "location": "Port", "notes": "test"}
    res = requests.post(f"{BASE}/add", data=data)
    assert res.status_code == 200
    res = requests.post(f"{BASE}/query", json={"ids": ["X1"]})
    assert res.status_code == 200
    detail = res.json()["details"][0]
    assert detail["status"] == "created"
    assert detail["location"] == "Port"

def test_health():
    res = requests.get(f"{BASE}/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_bad_request_errors():
    # we have two valid formats {"ids":["item1","item2"...]} or {"ids":"item1"}
    errors:list[Dict] = [
        {"ids":["2",["1","3"]]}, ## nested list output errors
        {"ids":1}, ## incorrect type
        {"IDS":"1"} ## doesn't follow format
        ]
    ## 500 error can only be tested by adding runtime errors to the server
    ## ex: error = shipments["12"] ## this will return an error if placed at the beginning
    error_code = [400, 500, 404]
    if gethealth():
        for i in errors:
            payload = json.dumps(i)
            res = requests.post(f"{BASE}/query", data=payload)
            assert res.status_code in error_code
        res = requests.post(f"{BASE}/querys")
        assert res.status_code in error_code
            

def queryships(single:bool=False):
    if single:
        ids = {"ids":"1"}
    else:
        ids = {"ids":["4", "5", "6"]}
    before = time.perf_counter()
    if gethealth():
        payload = json.dumps(ids)
        res = requests.post(f"{BASE}/query", data=payload)
        result = res.json()
        print("Query Results")
        for i in result["details"]:
            print(f"id: {i["id"]}, status: {i["status"]}, notes:{i["notes"]}, location:{i["location"]}")
        print(f"Took: {time.perf_counter()-before:.4f} to query")
        return True
    return False

def gethealth():
    try:
        res = requests.get(f"{BASE}/health")
        res.raise_for_status()
        payload = res.json()
        return payload.get("status") == "ok"
    except requests.RequestException:
        return False


if __name__ == "__main__":
    queryships()
    #test_bad_request_errors()