#!/bin/bash
# test_03_history.sh
# Test 3: GET /congestion/history — verify time-series for location 1 over 7 days.
#
# Usage:
#   export API_BASE=http://localhost:8000
#   bash tests/test_03_history.sh
#
# Expected:
#   - HTTP 200
#   - Results ordered oldest-first (ascending timestamp)
#   - All readings have location_id == 1
#   - At least 1 reading (14-day dataset has ~672 readings for location 1 over 7 days)

API_BASE="${API_BASE:-http://localhost:8000}"
ENDPOINT="$API_BASE/congestion/history?location_id=1&days=7&limit=1000"

echo "=== Test 3: GET /congestion/history (location_id=1, 7 days) ==="
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

python3 - <<EOF
import sys, json

body = '''$body'''
try:
    readings = json.loads(body)
except json.JSONDecodeError as e:
    print(f"FAIL: could not parse JSON — {e}")
    sys.exit(1)

n = len(readings)
print(f"Readings returned: {n}")

if n == 0:
    print("FAIL: expected at least 1 reading, got 0.")
    sys.exit(1)

# Check all belong to location 1
wrong_loc = [r for r in readings if r["location_id"] != 1]
if wrong_loc:
    print(f"FAIL: {len(wrong_loc)} readings have location_id != 1")
    sys.exit(1)

# Check ascending order
timestamps = [r["timestamp"] for r in readings]
if timestamps != sorted(timestamps):
    print("FAIL: readings are not in ascending timestamp order.")
    sys.exit(1)

# Summary stats
levels = [r["congestion_level"] for r in readings]
print(f"Location name: {readings[0].get('location_name', 'unknown')}")
print(f"Time range:    {timestamps[0][:16]} → {timestamps[-1][:16]}")
print(f"Avg congestion: {sum(levels)/len(levels):.2f}/10")
print(f"Max congestion: {max(levels):.2f}/10")
print(f"Min congestion: {min(levels):.2f}/10")

print("\nSample (first 3 readings):")
for r in readings[:3]:
    print(f"  {r['timestamp'][:16]}  level={r['congestion_level']:.2f}  speed={r.get('speed_mph','?')} mph  vol={r.get('volume','?')}")

print("\nPASS: /congestion/history returns ordered, valid time-series for location 1.")
EOF

if [ $? -ne 0 ]; then exit 1; fi