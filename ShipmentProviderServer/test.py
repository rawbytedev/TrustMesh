import json
import requests

url = "http://127.0.0.1:8000"

"""
We only have 3 options
/health - checks if server is up and running; also give a summary of how much items where tracked
/shipment/id - output details related to a shipment using it's ID, with autodebug=True, create a new shipment if it doesn't exist and return it
/shipment/id/update - can be used to both create new details, or update details of other shipments
"""
def selectShipment(action:int, id:int=0):
    shipment_id = id
    options ={
    1:f"{url}/health",
    2:f"{url}/shipment/{shipment_id}",
    3:f"{url}/shipment/{shipment_id}/update",
    4:f"{url}/shipments"
    }
    return options[action]

def updateshipment(status, location, notes,url):
    update = {
        "status":status,
        "location":location,
        "notes":notes
    }
    payload = json.dumps(update) ## production needs a better encoder
    re = requests.post(url, payload)
    print(f"Updating Shipment")
    print(f"Results: Status code: {re.status_code}")
    out = json.loads(re.text)
    print(f"shipment ID: {out["data"]["shipment_id"]}\nStatus: {out["data"]["status"]}\nlocation: {out["data"]["location"]}\nnotes: {out["data"]["notes"]}\ntimestamp: {out["data"]["timestamp"]}")


def queryships():
    ids = {"ids":["1", "2", "3"]}
    if gethealth():
        payload = json.dumps(ids)
        res = requests.post(url+"/query", data=payload)
        result = json.loads(res.text)
        print(result)
        print("Query Results")
        [print(f"id: {i["id"]}, status: {i["status"]}, notes:{i["notes"]}")for i in result["details"]]
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