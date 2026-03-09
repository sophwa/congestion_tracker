#!/bin/bash
# run_all_tests.sh
# Runs all City Congestion Tracker tests in sequence.
#
# Usage:
#   # 1. Start the API in another terminal: uvicorn app:app --reload --port 8000
#   # 2. Run from the repo root:
#   bash tests/run_all_tests.sh
#
# Override the API base URL for deployed testing:
#   API_BASE=https://your-deployed-api.com bash tests/run_all_tests.sh

set -e  # stop on first failure

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

export API_BASE="${API_BASE:-http://localhost:8000}"

echo "======================================================"
echo "  City Congestion Tracker — Full Test Suite"
echo "  API base: $API_BASE"
echo "======================================================"
echo ""

# --- Local data/model tests (no API needed) ---
echo ">>> Running local data tests (no API required)..."
python3 "$SCRIPT_DIR/test_local.py"
echo ""

# --- Live API tests ---
echo ">>> Running live API tests against $API_BASE ..."
echo ""
bash "$SCRIPT_DIR/test_01_locations.sh"
echo ""
bash "$SCRIPT_DIR/test_02_current.sh"
echo ""
bash "$SCRIPT_DIR/test_03_history.sh"
echo ""

echo "======================================================"
echo "  All tests passed."
echo "======================================================"
