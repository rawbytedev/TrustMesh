"""
Docstring for feedback_server
This is the server used by the AI it provides feedback regarding shipments status
in real use case the shipment provider sets it up to allow Ai to perform queries
"""
from urllib import request
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, List
import datetime

app = FastAPI(title="TrustMesh Feedback Server")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class QueryRequest(BaseModel):
    ids: list[str] | str

## End of UI
debugmode:bool = True
# In-memory store for shipments
shipments: Dict[str, Dict] = {}
class ShipmentUpdate(BaseModel):
    status: str = None   # created | in_transit | delayed | delivered | anomaly
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
"""
Take in a complete list of shipments id or a single shipment id
"""
@app.post("/query")
def query_shipments(req: QueryRequest):
    ids = req.ids
    if isinstance(ids, str):
        details = [get_shipment_detail(ids)]
    else:
        details = [get_shipment_detail(i) for i in ids]
    return {"details":details}

# helper function: retrieve shipments from storage
def get_shipment_detail(ship_id:str):
    if ship_id in shipments:
        return {"id":ship_id, **shipments[ship_id]}
    else:
        if debugmode:
            shipments[ship_id] = {"id":ship_id, "status":"Debug", "location":"LocalHost","notes":"Debug",  "timestamp":timestamp()} 
            return shipments[ship_id]
        return {"id":ship_id, "status":"Unknow", "notes":"not available", "location":"Unknow","timestamp":timestamp()}

## This is the entry point of App
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request":request, "shipments": shipments, "debug":debugmode})

## Allow to add shipments details from dashboard
@app.post("/add", response_class=HTMLResponse)
def add_shipment(request: Request, id:str =Form(...), status:str=Form(...),location:str =Form(...),notes:str=Form("")):
    shipments[id]= {"status":status, "location":location, "notes":notes, "timestamp":timestamp()} 
    return templates.TemplateResponse("index.html", {"request": request, "shipments":shipments, "debug":debugmode})

@app.post("/autoadd", response_class=HTMLResponse)
def setautoadd(request: Request):
    if debugmode:
        print("accessing")
        SetDebug(False)
        return templates.TemplateResponse("index.html", {"request": request, "shipments":shipments, "debug":False})
    print("seconds")
    SetDebug(True)
    return templates.TemplateResponse("index.html", {"request": request, "shipments":shipments, "debug":True})

def SetDebug(boo:bool):
    debugmode=boo
    return


@app.get("/health")
def health():
    return {"status": "ok"}
    #return {"status": "ok", "shipments_tracked": len(shipments)}


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()