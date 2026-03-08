#!/bin/bash
# test_01_locations.sh
# Test 1: GET /locations — verify the API returns all 20 monitored locations.
#
# Usage:
#   export API_BASE=http://localhost:8000   # or your deployed URL
#   bash tests/test_01_locations.sh
#
# Expected: JSON array of 20 objects, each with keys id, name, type, lat, lon.

API_BASE="${API_BASE:-http://localhost:8000}"
ENDPOINT="$API_BASE/locations"

echo "=== Test 1: GET /locations ==="
echo "Calling: $ENDPOINT"
echo ""

response=$(curl -s -w "\n%{http_code}" "$ENDPOINT")
body=$(echo "$response" | head -n -1)
code=$(echo "$response" | tail -n 1)

echo "HTTP Status: $code"
echo ""

if [ "$code" != "200" ]; then
  echo "FAIL: expected HTTP 200, got $code"
  exit 1
fi

count=$(echo "$body" | python3 -c "import sys, json; d = json.load(sys.stdin); print(len(d))")
echo "Location count: $count"

if [ "$count" -ne 20 ]; then
  echo "FAIL: expected 20 locations, got $count"
  exit 1
fi

# Check first location has required keys
keys=$(echo "$body" | python3 -c "
import sys, json
d = json.load(sys.stdin)
keys = sorted(d[0].keys())
print(keys)
")
echo "First location keys: $keys"

# Pretty-print first 3 entries
echo ""
echo "First 3 locations:"
echo "$body" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for loc in d[:3]:
    print(f\"  [{loc['id']}] {loc['name']} ({loc['type']}) lat={loc['lat']} lon={loc['lon']}\")
"

echo ""
echo "PASS: /locations returns 20 locations with correct schema."