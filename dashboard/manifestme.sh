#!/bin/bash
# manifestme.sh
# Regenerate manifest.json for the Congestion Tracker Shiny dashboard.
# Run from the repo root: bash dashboard/manifestme.sh

pip install rsconnect-python
rsconnect write-manifest shiny dashboard