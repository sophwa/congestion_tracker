"""
test_local.py
Local unit tests for the City Congestion Tracker.
Tests run against the CSV files and the data generation logic —
no network, no Supabase needed.

Usage:
    cd 05_hackathon/congestion_tracker
    python3 tests/test_local.py
"""

import csv
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_csv(name: str) -> list[dict]:
    path = DATA_DIR / name
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def run_test(name: str, fn):
    try:
        fn()
        print(f"  PASS  {name}")
        return True
    except AssertionError as e:
        print(f"  FAIL  {name}: {e}")
        return False


# ---------------------------------------------------------------------------
# Test 1: locations.csv structure
# ---------------------------------------------------------------------------
def test_locations_count():
    rows = load_csv("locations.csv")
    assert len(rows) == 20, f"Expected 20 locations, got {len(rows)}"


def test_locations_schema():
    rows = load_csv("locations.csv")
    required = {"id", "name", "type", "lat", "lon"}
    for row in rows:
        missing = required - set(row.keys())
        assert not missing, f"Missing columns: {missing} in row {row}"


def test_locations_types():
    rows = load_csv("locations.csv")
    valid_types = {"intersection", "segment", "zone"}
    for row in rows:
        assert row["type"] in valid_types, f"Invalid type '{row['type']}' for {row['name']}"


# ---------------------------------------------------------------------------
# Test 2: readings.csv structure
# ---------------------------------------------------------------------------
def test_readings_count():
    rows = load_csv("readings.csv")
    # 21-day rolling window * 96 intervals/day * 20 locations ≈ 38,000–41,000 rows
    # Exact count varies slightly based on time of day when data was generated.
    n = len(rows)
    assert 38_000 <= n <= 41_000, f"Expected ~40,320 readings (21-day window), got {n}"


def test_readings_schema():
    rows = load_csv("readings.csv")
    required = {"id", "location_id", "timestamp",
                "congestion_level", "speed_mph", "volume"}
    sample = rows[:10]
    for row in sample:
        missing = required - set(row.keys())
        assert not missing, f"Missing columns: {missing}"


def test_readings_congestion_range():
    rows = load_csv("readings.csv")
    bad = [r for r in rows if not (0 <= float(r["congestion_level"]) <= 10)]
    assert len(
        bad) == 0, f"{len(bad)} readings have congestion_level outside [0, 10]"


def test_readings_speed_range():
    rows = load_csv("readings.csv")
    bad = [r for r in rows if not (5 <= float(r["speed_mph"]) <= 45)]
    assert len(bad) == 0, f"{len(bad)} readings have speed_mph outside [5, 45]"


def test_readings_location_ids():
    rows = load_csv("readings.csv")
    ids = {int(r["location_id"]) for r in rows}
    assert ids == set(
        range(1, 21)), f"Unexpected location IDs: {ids - set(range(1, 21))}"


def test_readings_timestamp_format():
    rows = load_csv("readings.csv")
    from datetime import datetime
    sample = rows[:100]
    for row in sample:
        try:
            datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            assert False, f"Bad timestamp format: {row['timestamp']}"


# ---------------------------------------------------------------------------
# Test 3: Congestion model — peak hours higher than night
# ---------------------------------------------------------------------------
def test_peak_vs_night_congestion():
    rows = load_csv("readings.csv")
    from datetime import datetime

    am_peak = [float(r["congestion_level"]) for r in rows
               if 7 <= datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S").hour < 9]
    night = [float(r["congestion_level"]) for r in rows
             if datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S").hour < 5]

    avg_peak = sum(am_peak) / len(am_peak)
    avg_night = sum(night) / len(night)

    assert avg_peak > avg_night, (
        f"Expected AM peak ({avg_peak:.2f}) > night ({avg_night:.2f})"
    )


def test_weekday_vs_weekend():
    rows = load_csv("readings.csv")
    from datetime import datetime

    weekday = [float(r["congestion_level"]) for r in rows
               if datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S").weekday() < 5]
    weekend = [float(r["congestion_level"]) for r in rows
               if datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S").weekday() >= 5]

    avg_wd = sum(weekday) / len(weekday)
    avg_we = sum(weekend) / len(weekend)

    assert avg_wd > avg_we, (
        f"Expected weekday avg ({avg_wd:.2f}) > weekend avg ({avg_we:.2f})"
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
TESTS = [
    ("Locations: correct count (20)",              test_locations_count),
    ("Locations: required columns present",        test_locations_schema),
    ("Locations: valid type values",               test_locations_types),
    ("Readings: correct count (~40,320, 21-day window)", test_readings_count),
    ("Readings: required columns present",         test_readings_schema),
    ("Readings: congestion_level in [0, 10]",
     test_readings_congestion_range),
    ("Readings: speed_mph in [5, 45]",             test_readings_speed_range),
    ("Readings: location_ids 1-20 only",           test_readings_location_ids),
    ("Readings: timestamp format correct",         test_readings_timestamp_format),
    ("Model: AM peak > night congestion",          test_peak_vs_night_congestion),
    ("Model: weekday > weekend congestion",        test_weekday_vs_weekend),
]

if __name__ == "__main__":
    print("City Congestion Tracker — Local Data Tests")
    print("=" * 50)
    passed = sum(run_test(name, fn) for name, fn in TESTS)
    total = len(TESTS)
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    sys.exit(0 if passed == total else 1)
