# Gantry Robot Code

Docker-based stack for running a FastAPI application with GraphDB that operate the gantry robot.

- FastAPI provides a web dashboard and JSON API for controlling and monitoring the gantry robot agent.
- GraphDB stores the state of the system (operation mode, location, focus, resources, temporal metadata). Gantry robot operations are expressed using the semantics formalized by the [![Agents in Construction (AiC)](https://img.shields.io/badge/github-Agents_in_Construction_(AiC)_ontology-blue?logo=github)](https://github.com/DigiConstructLab-TU-Delft/AiC-Ontology) ontology.

The FastAPI app is located in `fastapi/` and connects to the GraphDB repository `prodRepo`.


---

## Structure

```
code/
├── fastapi/                        # FastAPI application and gantry robot control code
│   ├── app/                        # Python application package
│   │   ├── templates/              # Jinja2 templates and frontend assets served by FastAPI
│   │   │   ├── assets/             # Static frontend assets used by the templates
│   │   │   │   ├── css/            # Stylesheets and icon font CSS
│   │   │   │   │   └── style.css   # Project-specific dashboard styling
│   │   │   │   └── img/            # Logos and favicon image assets
│   │   │   │       ├── SMF4INFRA_Logo_Color.png
│   │   │   │       ├── TU-Delft_favicon_*.png
│   │   │   │       └── TUDelft_logo.png
│   │   │   ├── partialHTML/        # Reusable HTML template fragments
│   │   │   │   └── head-links.html # Shared page metadata, CSS links, and favicon links
│   │   │   ├── index.html          # Main gantry robot dashboard page
│   │   │   └── resetDB.html        # Database reset/status page
│   │   ├── config_agent.py         # Gantry robot configuration values
│   │   ├── config_network.py       # Network-related configuration values
│   │   ├── gantry_host.py          # Gantry robot hardware/event loop process
│   │   ├── graphdb_operations.py   # GraphDB endpoint setup and SPARQL query/update helper functions
│   │   ├── main.py                 # FastAPI entrypoint; defines routes, templates, middleware, and health checks
│   │   ├── models.py               # Pydantic request and response models
│   │   └── services.py             # Service layer for robot state, operations, and GraphDB interaction
│   ├── Dockerfile                  # Builds the Python image used by the API and motor worker services
│   └── requirements.txt            # Python dependencies for the FastAPI and gantry host services
├── graphdb/                        # GraphDB data, imports, and repository configuration
├── license-file/                   # Local GraphDB license file location
├── .env                            # Local environment variables
├── docker-compose.yaml             # Defines the FastAPI, motor worker, GraphDB, and GraphDB initialization services
└── README.md                       # This file
```

---

## Prerequisites

- Docker
- Docker Compose
- GraphDB license file
- Ports 8000 and 7200 available
- LEGO® Build HAT compatible hardware (for `buildhat`)

---

## Dependencies

[![FastAPI](https://img.shields.io/badge/fastapi%5Bstandard%5D-package-009688?logo=fastapi)](https://github.com/fastapi/fastapi)

[![Uvicorn](https://img.shields.io/badge/uvicorn%5Bstandard%5D-package-499848?logo=python)](https://github.com/Kludex/uvicorn)

[![Requests](https://img.shields.io/badge/requests-package-3776AB?logo=python)](https://github.com/psf/requests)

[![Motor](https://img.shields.io/badge/motor-package-47A248?logo=mongodb)](https://github.com/mongodb/motor)

[![Build HAT](https://img.shields.io/badge/buildhat-package-C51A4A?logo=raspberrypi)](https://github.com/RaspberryPiFoundation/python-build-hat)

Frontend assets are in `fastapi/app/templates/assets/`.

All dependencies and GraphDB are subject to their own licenses.


---

## Setup

### 1. License

Place the license file at:

```bash
license-file/graphdb.license
```

### 2. Start

```bash
docker compose up --build
```

### 3. Access

- Dashboard: [http://localhost:8000](http://localhost:8000/)
- Health: [http://localhost:8000/health](http://localhost:8000/health)
- Reset: [http://localhost:8000/resetDB](http://localhost:8000/resetDB)
- GraphDB: [http://localhost:7200](http://localhost:7200/)


### 4. Stop

```bash
docker compose down
```

---


## Using `/JSONrequest`

All backend commands are sent as `POST` requests to `http://localhost:8000/JSONrequest` with a shared JSON envelope:

```json
{
  "call_id": "unique-client-call-id",
  "function_name": "function_to_call",
  "parameters": {}
}
```

The response echoes the `call_id` and wraps the service response in `results`.

The available `/JSONrequest` functions are:

| function_name | Purpose | Main parameters |
|---|---|---|
| get_dataForUI | Returns dashboard data (operation mode, requested operations) | none |
| update_mode | Updates the gantry robot’s operation mode | new_mode |
| get_mode | Gets the current operation mode | modeSet, optional pointInTime |
| get_modeLog | Retrieves operation mode history | modeSet, optional pointInTime |
| update_location | Updates the operating location | new_location |
| get_location | Gets the current operating location | optional pointInTime, optional timeResolution |
| start_focus | Starts focusing on an element | focus, focusClass |
| stop_focus | Stops focusing on an element | focus |
| get_focus | Retrieves active focus elements | focusClass, optional pointInTime |
| request_gantryRobotOperation | Adds an operation to the queue | operationType; Transport: pickUpLocation, dropOffLocation, optional focus, optional requestID; Calibration: optional calibrationType, optional requestID |
| get_requestedGantryRobotOperations | Returns queued operations (only in Idle mode) | none |
| cancel_requestedGantryRobotOperation | Cancels a queued operation | requestID |
| confirm_elementPlacedForGantryRobotOperation | Marks a transport operation as placed, when the load to be carried is placed at the pick-up location | requestID |
| reset_DB | Resets the GraphDB database and reloads initial data | none |


### Examples

**1. Fetch the current operation mode**
```bash
curl -X POST http://localhost:8000/JSONrequest \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "get-mode-001",
    "function_name": "get_mode",
    "parameters": {
      "modeSet": "Internal"
    }
  }'
```

Example response:

```json
{
  "call_id": "get-mode-001",
  "results": {
    "pointInTime": "2026-04-30T12:00:00+02:00",
    "modeList": [
      {
        "mode": "Idle",
        "validFrom": "2026-04-30T11:55:00+02:00",
        "informationID_validFrom": "..."
      }
    ]
  }
}
```

**2. Update the operation mode**

```bash
curl -X POST http://localhost:8000/JSONrequest \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "update-mode-001",
    "function_name": "update_mode",
    "parameters": {
      "new_mode": "Maintenance"
    }
  }'
```

Example response:

```json
{
  "call_id": "update-mode-001",
  "results": {
    "message": "Operation mode updated to Maintenance"
  }
}
```

**3. Request a transport**

```bash
curl -X POST http://localhost:8000/JSONrequest \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "request-transport-001",
    "function_name": "request_gantryRobotOperation",
    "parameters": {
      "operationType": "Transport",
			"pickUpLocation": "B2",
			"dropOffLocation": "G1",
			"requestID": "API_123",
		  "focus": "Material_001"
    }
  }'
```

Example response:

```json
{
  "call_id": "request-transport-001",
  "results": {
    "message": "Transport requested."
  }
}
```

**4. Request calibration**

```bash
curl -X POST http://localhost:8000/JSONrequest \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "request-calibration-001",
    "function_name": "request_gantryRobotOperation",
    "parameters": {
      "operationType": "Calibration",
		  "calibrationType" : "Vertical",
			"requestID": "API_456"
    }
  }'
```

Example response:

```json
{
  "call_id": "request-calibration-001",
  "results": {
    "message": "Calibration requested."
  }
}
```

**5. Set the current focus**

```bash
curl -X POST http://localhost:8000/JSONrequest \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "start-focus-001",
    "function_name": "start_focus",
    "parameters": {
      "focus": "Material_001",
      "focusClass": "Material"
    }
  }'
```

Example response:

```json
{
  "call_id": "start-focus-001",
  "results": {
    "message": "Started focusing on Material_001"
  }
}
```

---

## Notes

- Operation queue (requested transports and calibrations) is in-memory and resets on container restart
- `prodRepo` is created on startup
- Data persists in `graphdb/data/`
- FastAPI runs on port 8000
- GraphDB runs on port 7200
- Timezone: Europe/Amsterdam

---

LEGO and the LEGO logo are trademarks of the LEGO Group of companies, which does not sponsor, authorize or endorse this research project. 