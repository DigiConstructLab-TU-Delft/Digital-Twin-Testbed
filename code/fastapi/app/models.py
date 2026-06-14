# models.py
# Classes for the scripts controlling the gantry robot of the digital twin testbed described in:
# Čustović, I. et al. (2026). Experimenting with Digital Twins: a LEGO®-based Modular Testbed for Systematic Evaluation. EC3 Conference 2026. Corfu, Greece. Available at: https://doi.org/10.35490/EC3.2026.233.
#
# Copyright (c) 2026 Irfan Čustović, Emilio Murillo Sierra, Ranjith K. Soman, Daniel M. Hall | TU Delft
# Licensed under the MIT License.
# See the 'licenses/' folder in the repository root for details.


from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime

class RequestData(BaseModel):
    call_id: str
    function_name: str
    parameters: Dict[str, Any]

class ResultData(BaseModel):
    call_id: str
    results: Dict[str, Any]
