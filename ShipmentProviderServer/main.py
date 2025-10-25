"""
Docstring for feedback_server
This is the server used by the AI it provides feedback regarding shipments status
in real use case the shipment provider sets it up to allow Ai to perform queries
"""
from fastapi import FastAPI,Request, Form
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
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
    ids: Union[List[str], str] # list

# Error handling
"""
We handle errors manually to avoid leaking details to frontend or API users
"""
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request format or parameters."},
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Override default HTTP errors too
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail if exc.detail else "An error occurred."},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log the real error internally
    print(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Please try again later."},
    )

# Peform a single query and reply with shipment details in json
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

## entry point of App
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return index({"request":request, "shipments": shipments, "debug":app.state.debugmode})

## Add shipment details from dashboard
@app.post("/add", response_class=HTMLResponse)
def add_shipment(request: Request, id:str =Form(...), status:str=Form(...),location:str =Form(...),notes:str=Form("")):
    shipments[id]= {"status":status, "location":location, "notes":notes, "timestamp":timestamp()} 
    index({"request": request, "shipments":shipments, "debug":app.state.debugmode})
    return redirect()

## toggle debug mode (autoadd)
@app.post("/toggle_autoadd", response_class=HTMLResponse)
def toggle(request: Request):
    if app.state.debugmode:
        app.state.debugmode = False
        index({"request": request, "shipments":shipments, "debug":False})
        return redirect()
    app.state.debugmode = True
    index({"request": request, "shipments":shipments, "debug":True})
    return redirect()

## return the status of server
@app.get("/health")
def health():
    return {"status": "ok"}
    #return {"status": "ok", "shipments_tracked": len(shipments)}

# return to index using custom context
def index(context: Dict | None = None):
    if context is None:
        context = {}
    return templates.TemplateResponse("index.html", context=context, status_code=200)

## give current timestamp 
def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

## redirect to home page
def redirect():
    return RedirectResponse(url="/", status_code=303)