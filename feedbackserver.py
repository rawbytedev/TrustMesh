"""
Docstring for feedback_server
The AI only calls
"""
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, List
import datetime
import db ## later use

app = FastAPI(title="TrustMesh Feedback Server")
# mount files
## improv
app.mount("/static", StaticFiles(directory="static"), name="static")
# templates
templates = Jinja2Templates(directory="templates")
## UI
class QueryRequest(BaseModel):
    ids: list[str] | str

def get_shipment_detail(ship_id:str)
## End of UI
debug = True 
# In-memory store for shipments
shipments: Dict[str, Dict] = {}
## must remove 
class ShipmentUpdate(BaseModel):
    status: str   # created | in_transit | delayed | delivered | anomaly
    location: str = None
    notes: str = None

class ShipmentDict(BaseModel):
    ids: List[str] = []
## this function allow to add or edit shipment status (demo)
"""
 {
 "shipment_id":"",
 "update":{
    "status": "", # created | in_transit | delayed | delivered | anomaly
    "location": "", ## refers to destination
    "notes":"custom notes"
    }
 }
"""
@app.post("/shipment/{shipment_id}/update")
def update_shipment(shipment_id: str, update: ShipmentUpdate):
    shipments[shipment_id] = {
        "shipment_id": shipment_id,
        "status": update.status,
        "location": update.location,
        "notes": update.notes,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    return {"message": "Shipment updated", "data": shipments[shipment_id]}

## this is function used by FeedBack handler to query ship states
@app.get("/shipment/{shipment_id}")
def get_shipment(shipment_id: str):
    if debug == True and shipment_id not in shipments:
        shipments[shipment_id] = {
            "shipment_id": shipment_id,
        "status": "Created",
        "location": "NYC Port",
        "notes": "Auto Create",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    if shipment_id not in shipments:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipments[shipment_id]

@app.post("/shipments")
def batchShips(ships: ShipmentDict):
    output = {"ships":[]}
    for i in ships.ids:
        res = getships(i)
        if res == None:
            output["ships"].append({"id":i,"results":"Not Known Yet"})
        else:
            output["ships"].append(res)
    return output

def getships(shipment_id):
    if debug == True and shipment_id not in shipments:
        shipments[shipment_id] = {
            "shipment_id": shipment_id,
        "status": "Created",
        "location": "NYC Port",
        "notes": "Auto Create",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    if shipment_id not in shipments:
        return None
    return shipments[shipment_id]

@app.get("/health")
def health():
    return {"status": "ok", "shipments_tracked": len(shipments)}


