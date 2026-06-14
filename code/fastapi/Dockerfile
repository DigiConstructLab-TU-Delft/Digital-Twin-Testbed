#
# Docker file of the gantry robot of the digital twin testbed described in:
# Čustović, I. et al. (2026). Experimenting with Digital Twins: a LEGO®-based Modular Testbed for Systematic Evaluation. EC3 Conference 2026. Corfu, Greece. Available at: https://doi.org/10.35490/EC3.2026.233.
#
# Copyright (c) 2026 Irfan Čustović, Emilio Murillo Sierra, Ranjith K. Soman, Daniel M. Hall | TU Delft
# Licensed under the MIT License.
# See the 'licenses/' folder in the repository root for details.

FROM python:3.13-slim

# System deps (curl only for optional debugging)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# App environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Install deps first (better Docker layer caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app ./app

# Expose Uvicorn port
EXPOSE 8000

# Start server
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
