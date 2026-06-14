# services.py
# Script for the procedural / application logic of the gantry robot of the digital twin testbed described in:
# Čustović, I. et al. (2026). Experimenting with Digital Twins: a LEGO®-based Modular Testbed for Systematic Evaluation. EC3 Conference 2026. Corfu, Greece. Available at: https://doi.org/10.35490/EC3.2026.233.
#
# Copyright (c) 2026 Irfan Čustović, Emilio Murillo Sierra, Ranjith K. Soman, Daniel M. Hall | TU Delft
# Licensed under the MIT License.
# See the 'licenses/' folder in the repository root for details.


from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime
from typing import Any, Dict

from fastapi import HTTPException
from zoneinfo import ZoneInfo

from .graphdb_operations import (
    graphDBupdateStatements,
    graphDBgetValidStatements,
)
from .config_agent import thisAgentID


Params = Dict[str, str]
Binding = dict[str, Any]

logger = logging.getLogger(__name__)

AMSTERDAM_TZ = ZoneInfo("Europe/Amsterdam")
AIC_NS = "https://www.w3id.org/aic#"
EX_NS = "http://example.org/aic-example#"
KNOWN_NAMESPACES = (EX_NS, AIC_NS)

actionsQueue: list[list[str]] = []
_actions_queue_lock = asyncio.Lock()

calibrationCounter = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return the current Amsterdam time as an ISO timestamp."""
    return datetime.now(AMSTERDAM_TZ).isoformat()


def _point_in_time(params: Params) -> str:
    """Return the requested pointInTime, or default to now."""
    point_in_time = params.get("pointInTime")

    if not point_in_time:
        logger.info("No 'pointInTime' parameter provided; using current time.")
        return _now_iso()

    return point_in_time


def _required_present(params: Params, name: str) -> str:
    """
    Require that a parameter exists.

    Empty strings are accepted because some API calls may intentionally pass
    an empty value to GraphDB.
    """
    value = params.get(name)

    if value is None:
        raise HTTPException(status_code=400, detail=f"Missing '{name}' parameter.")

    return value


def _required_non_empty(params: Params, name: str) -> str:
    """Require that a parameter exists and is not an empty string."""
    value = params.get(name)

    if not value:
        raise HTTPException(status_code=400, detail=f"Missing '{name}' parameter.")

    return value


def _strip_prefix(value: str) -> str:
    """
    Normalize GraphDB IRI results to local names.

    """
    if not value:
        return value

    for namespace in KNOWN_NAMESPACES:
        if value.startswith(namespace):
            return value[len(namespace):]

    if value.startswith(("aic:", "ex:")):
        return value.split(":", 1)[1]

    return value


def _binding_value(binding: Binding, key: str) -> str:
    """Extract the raw string value for a binding field."""
    return binding[key]["value"]


def _binding_object(binding: Binding) -> str:
    """Extract and normalize the object value from a GraphDB binding."""
    return _strip_prefix(_binding_value(binding, "object"))


def _binding_subject(binding: Binding) -> str:
    """Extract and normalize the subject value from a GraphDB binding."""
    return _strip_prefix(_binding_value(binding, "subject"))


def _temporal_fields(binding: Binding) -> dict[str, str]:
    """
    Extract standard validity metadata from a GraphDB binding.

    GraphDB may return open-ended statements without validUntil, so this field
    is only included when present.
    """
    fields = {
        "validFrom": _binding_value(binding, "validFrom"),
        "informationID_validFrom": _strip_prefix(
            _binding_value(binding, "informationID_validFrom")
        ),
    }

    if "validUntil" in binding:
        fields.update(
            {
                "validUntil": _binding_value(binding, "validUntil"),
                "informationID_validUntil": _strip_prefix(
                    _binding_value(binding, "informationID_validUntil")
                ),
            }
        )

    return fields


def _format_object_binding(binding: Binding, field_name: str) -> dict[str, str]:
    """Format common GraphDB object bindings such as mode, location, or focus."""
    return {
        field_name: _binding_object(binding),
        **_temporal_fields(binding),
    }


def _format_resource_request(binding: Binding) -> dict[str, str]:
    """Convert a GraphDB resource request binding into the API response shape."""
    return {
        "agent": _binding_subject(binding),
        "resource": _binding_object(binding),
        "location": _strip_prefix(_binding_value(binding, "location")),
        "validFrom": _binding_value(binding, "validFrom"),
        "informationID_validFrom": _strip_prefix(
            _binding_value(binding, "informationID_validFrom")
        ),
    }


def _format_resource_supply(binding: Binding) -> dict[str, str]:
    """Convert a GraphDB resource supply binding into the API response shape."""
    return {
        "agent": _binding_subject(binding),
        "resource": _binding_object(binding),
        "location": _strip_prefix(_binding_value(binding, "location")),
        "validAt": _binding_value(binding, "validAt"),
        "informationID_validAt": _strip_prefix(
            _binding_value(binding, "informationID_supply_validAt")
        ),
    }


def _format_time_in_mode(now: datetime, valid_from_raw: str) -> str:
    """Return a human-readable duration for how long the agent has been in a mode."""
    valid_from = datetime.fromisoformat(valid_from_raw)

    # Some GraphDB timestamps may be timezone-naive. Treat them as local time.
    if valid_from.tzinfo is None:
        valid_from = valid_from.replace(tzinfo=AMSTERDAM_TZ)

    total_secs = int((now - valid_from).total_seconds())
    mins, secs = divmod(total_secs, 60)

    return f"{mins} min {secs} sec" if mins else f"{secs} sec"


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

async def getDataForUI(params: Params):
    """
    Build the current UI payload for the agent dashboard.

    This combines the active mode, current queue, and open resource
    requests/supplies into one response.
    """
    now = datetime.now(AMSTERDAM_TZ)
    point_in_time = now.isoformat()

    mode_data = await getMode({"modeSet": "Internal", "pointInTime": point_in_time})
    mode_list = mode_data.get("modeList", [])

    if not mode_list or not mode_list[0].get("mode"):
        raise HTTPException(
            status_code=400,
            detail="No valid 'agentMode' in getMode response.",
        )

    agent_mode = mode_list[0]["mode"]
    time_in_mode = _format_time_in_mode(now, mode_list[0]["validFrom"])


    return {
        "pointInTime": point_in_time,
        "agentID": thisAgentID.replace("-", " "),
        "agentMode": agent_mode,
        "timeInMode": time_in_mode,
        "gantryRobotOperations": actionsQueue
    }


# ---------------------------------------------------------------------------
# Operation mode
# ---------------------------------------------------------------------------

async def updateMode(params: Params):
    """Update the agent's current operation mode in GraphDB."""
    new_mode = _required_present(params, "new_mode")
    point_in_time = _now_iso()

    statements_added_count = await graphDBupdateStatements(
        thisAgentID,
        "isInOperationMode",
        new_mode,
        "Performed",
        point_in_time,
        "insert-rigid",
        "OperationMode",
    )

    message = (
        f"Operation mode updated to {new_mode}"
        if statements_added_count > 0
        else f"Operation mode is already {new_mode}"
    )

    return {"message": message}


async def _get_mode(params: Params, query_type: str):
    """
    Shared implementation for current mode and historical mode queries.

    query_type controls whether GraphDB returns only the valid current mode
    or a historical mode log.
    """
    _required_non_empty(params, "modeSet")
    point_in_time = _point_in_time(params)

    bindings = await graphDBgetValidStatements(
        thisAgentID,
        "isInOperationMode",
        "",
        "Performed",
        point_in_time,
        query_type,
    )

    return {
        "pointInTime": point_in_time,
        "modeList": [
            _format_object_binding(binding, "mode")
            for binding in bindings
        ],
    }


async def getMode(params: Params):
    """Return the operation mode that is valid at pointInTime."""
    return await _get_mode(params, "select-valid-rigid")


async def getModeLog(params: Params):
    """Return historical operation mode statements up to pointInTime."""
    return await _get_mode(params, "select-past-rigid")


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

async def updateLocation(params: Params):
    """Update the agent's operating location in GraphDB."""
    new_location = _required_present(params, "new_location")
    point_in_time = _now_iso()

    statements_added_count = await graphDBupdateStatements(
        thisAgentID,
        "isOperatingIn",
        new_location,
        "Performed",
        point_in_time,
        "insert-rigid",
    )

    message = (
        f"Location updated to {new_location}"
        if statements_added_count > 0
        else f"Location is already {new_location}"
    )

    return {"message": message}


async def getLocation(params: Params):
    """
    Return the agent location valid at pointInTime.

    When timeResolution is 'pointInTime', the response uses validAt instead
    of the full validity interval.
    """
    point_in_time = _point_in_time(params)
    time_resolution = params.get("timeResolution")

    bindings = await graphDBgetValidStatements(
        thisAgentID,
        "isOperatingIn",
        "",
        "Performed",
        point_in_time,
        "select-valid-rigid",
    )

    bindings_list = []

    for binding in bindings:
        location = _binding_object(binding)

        if time_resolution == "pointInTime":
            bindings_list.append(
                {
                    "location": location,
                    "validAt": point_in_time,
                }
            )
        else:
            bindings_list.append(_format_object_binding(binding, "location"))

    return {
        "pointInTime": point_in_time,
        "locationList": bindings_list,
    }


# ---------------------------------------------------------------------------
# Execution focus
# ---------------------------------------------------------------------------

async def startFocus(params: Params):
    """Start a flexible focus statement for the given focus element."""
    focus = _required_present(params, "focus")
    focus_class = _required_present(params, "focusClass")
    point_in_time = _now_iso()

    statements_added_count = await graphDBupdateStatements(
        thisAgentID,
        "focusesOnElement",
        focus,
        "Performed",
        point_in_time,
        "insert-flexible-start",
        focus_class,
    )

    message = (
        f"Started focusing on {focus}"
        if statements_added_count > 0
        else f"Already focusing on {focus}"
    )

    return {"message": message}


async def stopFocus(params: Params):
    """Stop a flexible focus statement for the given focus element."""
    focus = _required_present(params, "focus")
    point_in_time = _now_iso()

    statements_added_count = await graphDBupdateStatements(
        thisAgentID,
        "focusesOnElement",
        focus,
        "Performed",
        point_in_time,
        "insert-flexible-stop",
    )

    message = (
        f"Stopped focusing on {focus}"
        if statements_added_count > 0
        else f"There was no valid focus on {focus}"
    )

    return {"message": message}


async def getFocus(params: Params):
    """Return active focus elements for the requested focus class."""
    point_in_time = _point_in_time(params)
    focus_class = _required_present(params, "focusClass")

    bindings = await graphDBgetValidStatements(
        thisAgentID,
        "focusesOnElement",
        "",
        "Performed",
        point_in_time,
        "select-valid-flexible",
        focus_class,
    )

    return {
        "pointInTime": point_in_time,
        "focusList": [
            _format_object_binding(binding, "focus")
            for binding in bindings
        ],
    }


# ---------------------------------------------------------------------------
# Gantry robot operations
# ---------------------------------------------------------------------------

async def requestGantryRobotOperation(params: Params):
    """
    Add a new gantry operation to the in-memory queue.

    Transport and Calibration requests have different positional list formats.
    """
    operation_type = _required_non_empty(params, "operationType")
    request_id = params.get("requestID") or f"UI_{random.randint(1000, 9999)}"

    if operation_type == "Transport":
        pick_up_location = _required_present(params, "pickUpLocation")
        drop_off_location = _required_present(params, "dropOffLocation")
        focus = params.get("focus") or ""

        # API requests wait for placement confirmation; UI requests are
        # considered placed immediately.
        status = "Open" if "API_" in request_id else "Placed"

        item = [
            request_id,
            "Transport",
            status,
            pick_up_location, 
            drop_off_location,
            focus,
        ]

    elif operation_type == "Calibration":
        calibration_type = params.get("calibrationType")

        if not calibration_type:
            logger.info(
                "No 'calibrationType' parameter provided; using 'Complete'."
            )
            calibration_type = "Complete"

        item = [
            request_id,
            "Calibration",
            "Open",
            calibration_type,
        ]

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported operationType '{operation_type}'.",
        )

    async with _actions_queue_lock:
        actionsQueue.append(item)

    return {"message": f"{operation_type} requested."}


async def getRequestedGantryRobotOperations(params: Params):
    """
    Return queued gantry operations only when the agent is Idle.

    """
    current_mode_data = await getMode({"modeSet": "Internal"})
    mode_list = current_mode_data.get("modeList", [])
    current_mode = mode_list[0]["mode"] if mode_list else None

    async with _actions_queue_lock:
        actions_queue_return = (
            [item.copy() for item in actionsQueue]
            if current_mode == "Idle"
            else []
        )

    return {
        "actionsQueue": actions_queue_return,
    }


async def cancelRequestedGantryRobotOperation(params: Params):
    """Remove a gantry operation from the queue by requestID."""
    request_id = _required_non_empty(params, "requestID")

    async with _actions_queue_lock:
        for index, item in enumerate(actionsQueue):
            if item[0] == request_id:
                del actionsQueue[index]
                return {"message": f"Request with ID {request_id} removed."}

    raise HTTPException(
        status_code=404,
        detail=f"No request with ID {request_id} was found.",
    )


async def confirmElementPlacedForGantryRobotOperation(params: Params):
    """
    Mark a queued transport operation as ready for pickup.

    """
    request_id = _required_non_empty(params, "requestID")

    async with _actions_queue_lock:
        for item in actionsQueue:
            if item[0] == request_id:
                item[2] = "Placed"

                confirmed_element = item[5] if len(item) > 5 else request_id

                return {
                    "message": (
                        f"Confirmation received: "
                        f"{confirmed_element} ready for pick-up."
                    )
                }

    raise HTTPException(
        status_code=404,
        detail=f"No request with ID {request_id} was found.",
    )

# ---------------------------------------------------------------------------
# DB and startup helpers
# ---------------------------------------------------------------------------

async def preloadDB(params: Params):
    """Initialize application state and preload required GraphDB statements."""
    global calibrationCounter

    calibrationCounter = 0
    point_in_time = _now_iso()

    await graphDBupdateStatements(
        thisAgentID,
        "",
        "",
        "Performed",
        point_in_time,
        "application-startup",
    )

    return {"message": "GraphDB prepared."}


async def resetDB(params: Params):
    """
    Reset GraphDB and run the normal startup preload.

    """
    await graphDBupdateStatements("", "", "", "", "", "reset-DB")
    await preloadDB({})

    return {"message": "GraphDB reset."}