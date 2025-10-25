import json
import time
import requests

url = "http://127.0.0.1:8000"

def queryships(single:bool=False):
    if single:
        ids = {"ids":"1"}
    else:
        ids = {"ids":["1", "2", "3", 1]}
    before = time.time()
    if gethealth():
        payload = json.dumps(ids)
        res = requests.post(url+"/query", data=payload)
        result = json.loads(res.text)
        print(result)
        print("Query Results")
        [print(f"id: {i["id"]}, status: {i["status"]}, notes:{i["notes"]}, location:{i["location"]}")for i in result["details"]]
        print(f"Took: {time.time()-before} to query")
        return True
    return False

def gethealth():
    res = requests.get(url+"/health")
    if res.status_code == 200:
        payload = json.loads(res.text)
        if payload["status"] == "ok":
            return True
    return False


if __name__ == "__main__":
    queryships()