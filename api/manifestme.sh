#!/bin/bash
# manifestme.sh
# Regenerate manifest.json for the Congestion Tracker FastAPI.
# Run from the repo root: bash api/manifestme.sh

pip install rsconnect-python
rsconnect write-manifest api api