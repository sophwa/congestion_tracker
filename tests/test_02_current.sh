#!/bin/bash
# test_02_current.sh
# Test 2: GET /congestion/current — verify current congestion readings.
#
# Usage:
#   export API_BASE=http://localhost:8000
#   bash tests/test_02_current.sh
#
# Expected: JSON array of readings, each with congestion_level in [0, 10].

API_BASE="${API_BASE:-http://localhost:8000}"
ENDPOINT="$API_BASE/congestion/current?window_minutes=30"

echo "=== Test 2: GET /congestion/current ==="
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

# Validate structure
python3 - <<EOF
import sys, json

body = '''$body'''
try:
    readings = json.loads(body)
except json.JSONDecodeError as e:
    print(f"FAIL: could not parse JSON — {e}")
    sys.exit(1)

print(f"Number of readings returned: {len(readings)}")

errors = []
for r in readings:
    for key in ("id", "location_id", "timestamp", "congestion_level"):
        if key not in r:
            errors.append(f"Missing key '{key}' in reading id={r.get('id','?')}")
    lvl = r.get("congestion_level", -1)
    if not (0 <= lvl <= 10):
        errors.append(f"congestion_level={lvl} out of range [0,10] for location_id={r.get('location_id','?')}")

if errors:
    for e in errors:
        print(f"FAIL: {e}")
    sys.exit(1)

# Print top 5 by congestion
top5 = sorted(readings, key=lambda x: x["congestion_level"], reverse=True)[:5]
print("\nTop 5 congested locations right now:")
for r in top5:
    name = r.get("location_name", r["location_id"])
    print(f"  {name}: {r['congestion_level']:.2f}/10")

print("\nPASS: /congestion/current returns valid readings with congestion_level in [0, 10].")
EOF

if [ $? -ne 0 ]; then exit 1; fi
