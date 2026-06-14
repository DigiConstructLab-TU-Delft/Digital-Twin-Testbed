# main.py
# Main fastAPI script for controlling the gantry robot of the digital twin testbed described in:
# Čustović, I. et al. (2026). Experimenting with Digital Twins: a LEGO®-based Modular Testbed for Systematic Evaluation. EC3 Conference 2026. Corfu, Greece. Available at: https://doi.org/10.35490/EC3.2026.233.
#
# Copyright (c) 2026 Irfan Čustović, Emilio Murillo Sierra, Ranjith K. Soman, Daniel M. Hall | TU Delft
# Licensed under the MIT License.
# See the 'licenses/' folder in the repository root for details.


from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from typing import Any, Dict, Callable

from pathlib import Path

from .models import RequestData, ResultData

from . import services

from .config_agent import thisAgentID

app = FastAPI(title="TU Delft DigiConstruct Lab - Gantry Robot")



origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Function mapping for JSON requests
function_map: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    "get_dataForUI": services.getDataForUI,
    "update_mode": services.updateMode,
    "get_mode": services.getMode,
    "get_modeLog": services.getModeLog,
    "update_location": services.updateLocation,
    "get_location": services.getLocation,
    "start_focus": services.startFocus,
    "stop_focus": services.stopFocus,
    "get_focus": services.getFocus,
    "request_gantryRobotOperation": services.requestGantryRobotOperation,
    "get_requestedGantryRobotOperations": services.getRequestedGantryRobotOperations, 
    "cancel_requestedGantryRobotOperation": services.cancelRequestedGantryRobotOperation,
    "confirm_elementPlacedForGantryRobotOperation": services.confirmElementPlacedForGantryRobotOperation,
    "reset_DB": services.resetDB
}

@app.post("/JSONrequest", response_model=ResultData)
async def process_request(data: RequestData) -> ResultData:
     
    print(f"{data.call_id} | Function: {data.function_name}, {data.parameters}")
    
    if data.function_name not in function_map:
        raise HTTPException(status_code=400, detail="Invalid function name.")

    service_func = function_map[data.function_name]

    try:
        result = await service_func(data.parameters)
    except TypeError as exc:
        raise HTTPException(status_code=400, detail=f"Parameter error: {exc}")

    results_dict = result if isinstance(result, dict) else {"value": result}

    return ResultData(call_id=data.call_id, results=results_dict)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory="app/templates")
app.mount("/templates", StaticFiles(directory="app/templates"), name="templates")


# Define URL routes for serving HTML files
@app.get("/")
async def serve_index(request: Request):
    """
    Serves the index.html template with dynamic data.
    """
    return templates.TemplateResponse(
        request,
        "index.html",
        context={
            "agentID": thisAgentID.replace("-", " "),
            "currentTag": "",
            "stationStatus": await services.getMode({"modeSet": "Internal"})
        }
    )

 
@app.on_event("startup")
async def startup_event():
    message = await services.preloadDB({})
    
@app.get("/health")
async def health():
    return {"ok": True}
    
@app.get("/resetDB")
async def serve_resetDB(request: Request):
    return templates.TemplateResponse(
        request,
        "resetDB.html",
        context={}
    )
        
@app.on_event("shutdown")
def shutdown_event():
    print("Bye.") 