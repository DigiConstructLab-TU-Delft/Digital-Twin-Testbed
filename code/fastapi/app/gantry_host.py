# gantry_host.py
# Script for interacting with the physical motors of the gantry robot of the digital twin testbed described in:
# Čustović, I. et al. (2026). Experimenting with Digital Twins: a LEGO®-based Modular Testbed for Systematic Evaluation. EC3 Conference 2026. Corfu, Greece. Available at: https://doi.org/10.35490/EC3.2026.233.
#
# Copyright (c) 2026 Irfan Čustović, Emilio Murillo Sierra, Ranjith K. Soman, Daniel M. Hall | TU Delft
# Licensed under the MIT License.
# See the 'licenses/' folder in the repository root for details.

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict

import requests
from buildhat import Motor
from zoneinfo import ZoneInfo


API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("API_TIMEOUT_SECONDS", "5"))

AMSTERDAM_TZ = ZoneInfo("Europe/Amsterdam")

POLL_IDLE_SECONDS = 1
POLL_ERROR_SECONDS = 5

# Optional: Let the gantry robot automatically calibrate itself
# after a fixed amount of operations performed.
CALIBRATE_AFTER_TRANSPORTS = 10

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Motor setup
# ---------------------------------------------------------------------------
# Each motor is connected to a fixed BuildHAT port. Keep these assignments in
# sync with the physical wiring of the gantry robot.

vertical_motor = Motor("A")       # Vertical claw movement
claw_motor = Motor("B")           # Claw open/close movement
longitudinal_motor = Motor("C")   # Longitudinal gantry movement
horizontal_motor = Motor("D")     # Horizontal gantry movement

# Default power limits protect the gantry robot during normal operation. 
# Some routines temporarily override these values for calibration or lifting.
claw_motor.plimit(0.55)
vertical_motor.plimit(0.55)
horizontal_motor.plimit(0.9)
longitudinal_motor.plimit(0.6)


# Predefined station coordinates: (horizontal, longitudinal).
stations = {
    "RestingPosition": (0, 0),
    "Storage": (0, 0),

    "A1": (320, -4000),
    "A2": (-340, -4000),

    "B1": (320, -3228),
    "B2": (-340, -3228),

    "C1": (320, -2152),
    "C2": (-340, -2152),

    "D1": (320, -1076),
    "D2": (-340, -1076),

    "E1": (320, 0),
    "E2": (-340, 0),

    "F1": (320, 1076),
    "F2": (-340, 1076),

    "G1": (320, 2152),
    "G2": (-340, 2152),

    "H1": (320, 3228),
    "H2": (-340, 3228),

    "I1": (320, 3650),
    "I2": (-340, 3650),
}

# Current gantry position in the same coordinate system as stations.
current_position = (0, 0)

calibrationCounter = 0


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return the current Amsterdam time as an ISO timestamp."""
    return datetime.now(AMSTERDAM_TZ).isoformat()


def _json_request(function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Build the standard payload expected by the central JSONrequest endpoint."""
    return {
        "call_id": "string",
        "function_name": function_name,
        "parameters": parameters,
    }


async def _post_json_request(
    function_name: str,
    parameters: Dict[str, Any],
    *,
    raise_for_status: bool = False,
) -> requests.Response:
    """
    Send a request to the central API without blocking the event loop.

    The motor API itself is synchronous, but API calls can still be moved to a
    worker thread so polling and status updates do not block the async loop.
    """
    payload = _json_request(function_name, parameters)

    def _post() -> requests.Response:
        return requests.post(
            f"{API_BASE}/JSONrequest",
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    response = await asyncio.to_thread(_post)

    if raise_for_status:
        response.raise_for_status()

    return response


async def sendUpdateModeMessage(mode):
    """Notify the API that the gantry robot entered a new operation mode."""
    await _post_json_request(
        "update_mode",
        {
            "pointInTime": _now_iso(),
            "new_mode": mode,
        },
    )


async def _sendUpdateLocationMessage(location):
    """Notify the API that the gantry robot is at a new logical location."""
    await _post_json_request(
        "update_location",
        {
            "pointInTime": _now_iso(),
            "new_location": location,
        },
    )


async def _sendStartFocus(focus):
    """Tell the API that the gantry robot started focusing on a material."""
    await _post_json_request(
        "start_focus",
        {
            "pointInTime": _now_iso(),
            "focus": focus,
            "focusClass": "Material",
        },
    )


async def _sendStopFocus(focus):
    """Tell the API that the gantry robot stopped focusing on a material."""
    await _post_json_request(
        "stop_focus",
        {
            "pointInTime": _now_iso(),
            "focus": focus,
            "focusClass": "Material",
        },
    )


async def _get_requested_gantry_robot_operations() -> list[list[Any]]:
    """Fetch pending gantry operations from the central API."""
    response = await _post_json_request(
        "get_requestedGantryRobotOperations",
        {},
        raise_for_status=True,
    )

    data = response.json()
    return data.get("results", {}).get("actionsQueue", [])


async def _cancel_requested_gantry_robot_operation(request_id: str) -> None:
    """Remove a completed or invalid operation from the central queue."""
    await _post_json_request(
        "cancel_requestedGantryRobotOperation",
        {
            "requestID": request_id,
        },
    )


# ---------------------------------------------------------------------------
# High-level gantry robot operations
# ---------------------------------------------------------------------------

async def calibrate(calibrationType):
    """Run the requested calibration routine and return the gantry robot to Idle."""
    global calibrationCounter

    await _sendUpdateLocationMessage("Site")
    await sendUpdateModeMessage("Calibrating")

    if calibrationType == "Complete":
        await calibrate_claw()
        await calibrate_vertical()
        await calibrate_horizontal()
        await calibrate_longitudinal()

    elif calibrationType == "Claw":
        await calibrate_claw()

    elif calibrationType == "Vertical":
        await calibrate_vertical()

    elif calibrationType == "Horizontal":
        await calibrate_horizontal()

    elif calibrationType == "Longitudinal":
        await calibrate_longitudinal()

    else:
        logger.warning("Unknown calibration type requested: %s", calibrationType)

    await _sendUpdateLocationMessage("RestingPosition")
    await sendUpdateModeMessage("Idle")

    return {"message": f"{calibrationType} calibration executed."}


async def transport(requestID, pickUpLocation, dropOffLocation, focus):
    """
    Execute one full transport cycle.

    """
    global calibrationCounter

    await _sendUpdateLocationMessage("Site")
    await sendUpdateModeMessage("Moving")

    if focus != "":
        await _sendStartFocus(focus)

    await move_to(pickUpLocation)

    await _sendUpdateLocationMessage(pickUpLocation)
    await sendUpdateModeMessage("PickingUp")

    await claw_down(685)

    await claw_close()

    await claw_up(690)

    await _sendUpdateLocationMessage("Site")
    await sendUpdateModeMessage("Moving")

    await move_to(dropOffLocation)

    await _sendUpdateLocationMessage(dropOffLocation)
    await sendUpdateModeMessage("DroppingOff")

    await claw_down(690)

    await claw_open()

    await claw_up(695)

    await _sendUpdateLocationMessage("Site")
    await sendUpdateModeMessage("Moving")

    await move_to("RestingPosition")

    await _sendUpdateLocationMessage("RestingPosition")
    await sendUpdateModeMessage("Idle")

    if focus != "":
        await _sendStopFocus(focus)

    calibrationCounter += 1

    if calibrationCounter == CALIBRATE_AFTER_TRANSPORTS:
        await calibrate("Complete")
        calibrationCounter = 0

    return {
        "message": (
            f"Transport from {pickUpLocation} to {dropOffLocation} executed."
        )
    }


# ---------------------------------------------------------------------------
# Calibration helpers
# ---------------------------------------------------------------------------

async def _run_until_stalled(
    motor: Motor,
    *,
    start_speed: int,
    stall_reads_needed: int,
    poll_interval: float,
) -> None:
    """
    Run a motor until its encoder position stops changing.

    This is used during calibration to find mechanical end stops. The motor is
    always stopped before returning, including if the task is cancelled.
    """
    motor.start(start_speed)

    no_change_count = 0
    last_position = motor.get_position()

    try:
        while True:
            await asyncio.sleep(poll_interval)

            current_position_reading = motor.get_position()

            if current_position_reading == last_position:
                no_change_count += 1
            else:
                no_change_count = 0

            if no_change_count >= stall_reads_needed:
                return

            last_position = current_position_reading

    finally:
        motor.stop()


async def calibrate_claw():
    """Calibrate the claw by opening to its end stop, then cycling closed/open."""
    claw_motor.plimit(0.55)
    claw_motor.run_for_degrees(-5, 10)

    # Negative degrees open the claw,
    # positive degrees close it.
    await _run_until_stalled(
        claw_motor,
        start_speed=-20,
        stall_reads_needed=10,
        poll_interval=0.01,
    )

    claw_motor.run_for_degrees(130, 20)    # Close fully
    claw_motor.run_for_degrees(-130, 20)   # Open fully


async def calibrate_vertical():
    """Calibrate vertical movement against its mechanical end stop."""
    
    # Positive degrees move upward,
    # negative degrees move downward
    await _run_until_stalled(
        vertical_motor,
        start_speed=20,
        stall_reads_needed=10,
        poll_interval=0.05,
    )

    vertical_motor.run_for_degrees(-790, 20)


async def calibrate_horizontal():
    """Calibrate horizontal movement against its mechanical end stop."""
    horizontal_motor.plimit(0.9)

    # Positive degrees move towards the RPi,
    # negative degrees move away from the RPi
    await _run_until_stalled(
        horizontal_motor,
        start_speed=30,
        stall_reads_needed=15,
        poll_interval=0.01,
    )

    horizontal_motor.run_for_degrees(-330, 30)


async def calibrate_longitudinal():
    """Calibrate longitudinal movement against its mechanical end stop."""
    longitudinal_motor.plimit(0.6)

    # Positive degrees move towards the calibration endpoint,
    # negative degrees move away from the calibration endpoint
    await _run_until_stalled(
        longitudinal_motor,
        start_speed=30,
        stall_reads_needed=3,
        poll_interval=0.1,
    )

    longitudinal_motor.plimit(1)
    longitudinal_motor.run_for_degrees(-3810, speed=20)
    longitudinal_motor.plimit(0.6)


# ---------------------------------------------------------------------------
# Low-level movement helpers
# ---------------------------------------------------------------------------

async def claw_close():
    """Close the claw by the calibrated fixed amount."""
    claw_motor.run_for_degrees(130, 20)


async def claw_open():
    """Open the claw by the calibrated fixed amount."""
    claw_motor.run_for_degrees(-130, 20)


async def claw_down(degrees):
    """Lower the claw by the requested number of motor degrees."""
    vertical_motor.plimit(0.80)
    vertical_motor.run_for_degrees(degrees, 20)
    vertical_motor.plimit(0.55)


async def claw_up(degrees):
    """Raise the claw by the requested number of motor degrees."""
    vertical_motor.plimit(0.80)
    vertical_motor.run_for_degrees(-degrees, 20)
    vertical_motor.plimit(0.55)


async def move_to(target):
    """
    Move the gantry to a named station.

    Movement order is longitudinal first, then horizontal.
    """
    global current_position

    longitudinal_motor.plimit(0.8)

    horizontal_target, longitudinal_target = stations[target]

    delta_longitudinal = longitudinal_target - current_position[1]
    if delta_longitudinal:
        longitudinal_motor.run_for_degrees(delta_longitudinal, 30)

    delta_horizontal = horizontal_target - current_position[0]
    if delta_horizontal:
        horizontal_motor.run_for_degrees(delta_horizontal, 20)

    longitudinal_motor.plimit(0.6)

    current_position = (horizontal_target, longitudinal_target)


# ---------------------------------------------------------------------------
# Queue processing
# ---------------------------------------------------------------------------

def _has_valid_transport_shape(item: list[Any]) -> bool:
    """Validate the positional queue format used for transport requests."""
    return (
        item[1] == "Transport"
        and item[3] in stations
        and item[4] in stations
    )


async def _process_transport_item(item: list[Any]) -> None:
    """Validate and execute a queued transport request."""
    request_id = item[0]

    if item[2] != "Placed":
        # Only execute transport requests that are ready.
        return

    if not _has_valid_transport_shape(item):
        logger.warning(
            "Unknown transport location or invalid request shape: %s",
            item,
        )
        await _cancel_requested_gantry_robot_operation(request_id)
        return

    await transport(
        request_id,
        item[3],
        item[4],
        item[5],
    )

    await _cancel_requested_gantry_robot_operation(request_id)


async def _process_calibration_item(item: list[Any]) -> None:
    """Validate and execute a queued calibration request."""
    request_id = item[0]

    await calibrate(item[3])
    await _cancel_requested_gantry_robot_operation(request_id)


async def _process_queue_item(item: list[Any]) -> None:
    """
    Process a single queue item.

    """

    logger.info("Received gantry operation: %s", item)

    operation_type = item[1]

    if operation_type == "Transport":
        await _process_transport_item(item)

    elif operation_type == "Calibration":
        await _process_calibration_item(item)

    else:
        logger.warning("Unknown gantry operation type: %s", operation_type)


async def main():
    print("-------------------------------------------")
    print("Gantry robot motors started. Waiting for requests.")
    print("-------------------------------------------")

    while True:
        try:
            items = await _get_requested_gantry_robot_operations()

            if not items:
                await asyncio.sleep(POLL_IDLE_SECONDS)
                continue

            # Process only the first available item.
            await _process_queue_item(items[0])

        except requests.RequestException:
            logger.exception("HTTP error while polling gantry operations.")
            await asyncio.sleep(POLL_ERROR_SECONDS)

        except Exception:
            logger.exception("Unexpected gantry robot error.")
            await asyncio.sleep(POLL_ERROR_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    asyncio.run(main())