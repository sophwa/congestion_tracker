# seed.py
# Seed the Supabase database with synthetic congestion data.
#
# Prerequisites:
#   pip install supabase python-dotenv
#
# Environment variables (in .env):
#   SUPABASE_URL  = https://xxxx.supabase.co
#   SUPABASE_KEY  = your-service-role-key   (use service role to bypass RLS on insert)
#
# Run from the data/ directory after generating CSVs:
#   cd data && python ../database/seed.py
#
# The script is idempotent: it truncates both tables before inserting.

import csv
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # service role key for seeding

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    sys.exit(1)

DATA_DIR = Path(__file__).parent.parent / "data"
LOCATIONS_CSV = DATA_DIR / "locations.csv"
READINGS_CSV = DATA_DIR / "readings.csv"

BATCH_SIZE = 500  # rows per upsert call (Supabase limit ~1 MB)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def coerce_location(row: dict) -> dict:
    return {
        "id":   int(row["id"]),
        "name": row["name"],
        "type": row["type"],
        "lat":  float(row["lat"]),
        "lon":  float(row["lon"]),
    }


def coerce_reading(row: dict) -> dict:
    return {
        "id":               int(row["id"]),
        "location_id":      int(row["location_id"]),
        # ISO string, Supabase accepts it
        "timestamp":        row["timestamp"],
        "congestion_level": float(row["congestion_level"]),
        "speed_mph":        float(row["speed_mph"]),
        "volume":           int(row["volume"]),
    }


def chunked(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # -- Locations -----------------------------------------------------------
    print("Loading locations.csv …")
    locs = [coerce_location(r) for r in load_csv(LOCATIONS_CSV)]
    print(f"  Upserting {len(locs)} locations …")
    supabase.table("locations").upsert(locs).execute()
    print("  Done.")

    # -- Readings ------------------------------------------------------------
    print("Loading readings.csv …")
    readings = [coerce_reading(r) for r in load_csv(READINGS_CSV)]
    total = len(readings)
    print(f"  Upserting {total:,} readings in batches of {BATCH_SIZE} …")
    for i, batch in enumerate(chunked(readings, BATCH_SIZE), start=1):
        supabase.table("congestion_readings").upsert(batch).execute()
        pct = i * BATCH_SIZE / total * 100
        print(
            f"  Batch {i}: {min(i*BATCH_SIZE, total):,}/{total:,} ({pct:.0f}%)")
    print("  Done.")

    print("\nDatabase seeded successfully.")


if __name__ == "__main__":
    main()
