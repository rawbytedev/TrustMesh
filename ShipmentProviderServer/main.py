"""
Docstring for feedback_server
This is the server used by the AI it provides feedback regarding shipments status
in real use case the shipment provider sets it up to allow Ai to perform queries
"""
from http.client import UNPROCESSABLE_CONTENT
from urllib import request
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, List, Union
import datetime


app = FastAPI(title="TrustMesh Feedback Server")
# In-memory store for shipments
shipments: Dict[str, Dict] = {} ## dictionary are mutable
app.state.debugmode = True ## bool are not so we use app.state
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class QueryRequest(BaseModel):
    ids: Union[list[str], str]

## End of UI
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
class CustomException(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
    def response(self):
        if self.status_code == 422:
            print("422 ERROR")

@app.exception_handler(CustomException)
async def exp(resquest: Request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message},
    )

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
        if app.state.debugmode:
            shipments[ship_id] = {"id":ship_id, "status":"Debug", "location":"LocalHost","notes":"Debug",  "timestamp":timestamp()} 
            return shipments[ship_id]
        return {"id":ship_id, "status":"Unknown", "notes":"not available", "location":"Unknown","timestamp":timestamp()}

## This is the entry point of App
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return index({"request":request, "shipments": shipments, "debug":app.state.debugmode})

## Allow to add shipments details from dashboard
@app.post("/add", response_class=HTMLResponse)
def add_shipment(request: Request, id:str =Form(...), status:str=Form(...),location:str =Form(...),notes:str=Form("")):
    shipments[id]= {"status":status, "location":location, "notes":notes, "timestamp":timestamp()} 
    return index({"request": request, "shipments":shipments, "debug":app.state.debugmode})

@app.post("/toggle_autoadd", response_class=HTMLResponse)
def toggle(request: Request):
    if app.state.debugmode:
        app.state.debugmode = False
        return index({"request": request, "shipments":shipments, "debug":False})
    app.state.debugmode = True
    return index({"request": request, "shipments":shipments, "debug":True})

@app.get("/health")
def health():
    return {"status": "ok"}
    #return {"status": "ok", "shipments_tracked": len(shipments)}

# return to index using custom context
def index(context: Dict | None = None):
    if context is None:
        context = {}
    return templates.TemplateResponse("index.html", context=context)


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()