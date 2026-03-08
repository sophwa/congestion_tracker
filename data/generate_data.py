# generate_data.py
# Synthetic data generator for City Congestion Tracker
# Generates realistic congestion readings for 20 city locations over 14 days
# Run: python generate_data.py  --> writes locations.csv and readings.csv

import csv
import random
from datetime import datetime, timedelta

random.seed(42)

# ---------------------------------------------------------------------------
# 1. Location definitions
# ---------------------------------------------------------------------------
LOCATIONS = [
    # id, name, type, lat, lon
    (1,  "Main St & 1st Ave",      "intersection", 42.4440, -76.5019),
    (2,  "College Ave & State St",  "intersection", 42.4474, -76.4875),
    (3,  "Seneca St & Tioga St",    "intersection", 42.4390, -76.4980),
    (4,  "Meadow St & Dryden Rd",   "intersection", 42.4350, -76.4900),
    (5,  "Route 13 North Segment",  "segment",      42.4600, -76.5100),
    (6,  "Route 96 East Segment",   "segment",      42.4500, -76.4700),
    (7,  "Elmira Rd Segment",       "segment",      42.4280, -76.5200),
    (8,  "Hanshaw Rd Segment",      "segment",      42.4700, -76.4600),
    (9,  "Downtown Zone",           "zone",         42.4430, -76.4990),
    (10, "University Area Zone",    "zone",         42.4490, -76.4840),
    (11, "West Hill Zone",          "zone",         42.4410, -76.5150),
    (12, "Cayuga Heights Zone",     "zone",         42.4680, -76.4780),
    (13, "South Hill Zone",         "zone",         42.4290, -76.4960),
    (14, "Northeast Zone",          "zone",         42.4620, -76.4680),
    (15, "Ithaca Commons",          "intersection", 42.4410, -76.4990),
    (16, "Green St & Cayuga St",    "intersection", 42.4400, -76.4973),
    (17, "Aurora St & Buffalo St",  "intersection", 42.4420, -76.5000),
    (18, "Cayuga St Corridor",      "segment",      42.4450, -76.4970),
    (19, "Stewart Ave Segment",     "segment",      42.4380, -76.4870),
    (20, "East State St Segment",   "segment",      42.4360, -76.4920),
]

# ---------------------------------------------------------------------------
# 2. Congestion model helpers
# ---------------------------------------------------------------------------
# base_level: typical mid-day off-peak congestion (0-10)
LOCATION_BASE = {loc_id: random.uniform(1.5, 4.5) for loc_id, *_ in LOCATIONS}


def congestion_level(loc_id: int, dt: datetime) -> float:
    """Return a realistic congestion score (0-10) for a location at a datetime."""
    base = LOCATION_BASE[loc_id]
    hour = dt.hour + dt.minute / 60.0
    weekday = dt.weekday()  # 0=Mon, 6=Sun

    # time-of-day multiplier: AM peak 7-9, PM peak 16-18
    if 7 <= hour < 9:
        tod = 2.0
    elif 16 <= hour < 18:
        tod = 2.2
    elif 9 <= hour < 16:
        tod = 1.2
    elif 6 <= hour < 7 or 18 <= hour < 20:
        tod = 1.4
    elif 20 <= hour < 23:
        tod = 0.8
    else:  # 23-6
        tod = 0.3

    # day-of-week multiplier
    if weekday < 5:   # weekday
        dow = 1.0
    elif weekday == 5:  # Saturday
        dow = 0.75
    else:              # Sunday
        dow = 0.5

    # slight random variation
    noise = random.gauss(0, 0.5)
    level = base * tod * dow + noise
    return max(0.0, min(10.0, round(level, 2)))


def speed_from_congestion(congestion: float) -> float:
    """Map congestion (0-10) to approximate speed in mph (5-45)."""
    speed = 45 - (congestion / 10.0) * 40 + random.gauss(0, 1.5)
    return max(5.0, min(45.0, round(speed, 1)))


def volume_from_congestion(congestion: float, loc_type: str) -> int:
    """Estimated vehicles per 15-min interval."""
    base_vols = {"intersection": 80, "segment": 60, "zone": 40}
    base = base_vols.get(loc_type, 60)
    volume = int(base * (0.5 + congestion / 10.0) + random.gauss(0, 5))
    return max(0, volume)


# ---------------------------------------------------------------------------
# 3. Generate readings
# ---------------------------------------------------------------------------
START = datetime(2026, 2, 23, 0, 0, 0)   # 14 days ago (relative to Mar 8)
END = datetime(2026, 3,  8, 23, 45, 0)
INTERVAL_MINUTES = 15


def generate_readings():
    rows = []
    reading_id = 1
    dt = START
    while dt <= END:
        for loc_id, name, loc_type, lat, lon in LOCATIONS:
            cl = congestion_level(loc_id, dt)
            sp = speed_from_congestion(cl)
            vo = volume_from_congestion(cl, loc_type)
            rows.append({
                "id":              reading_id,
                "location_id":     loc_id,
                "timestamp":       dt.strftime("%Y-%m-%d %H:%M:%S"),
                "congestion_level": cl,
                "speed_mph":       sp,
                "volume":          vo,
            })
            reading_id += 1
        dt += timedelta(minutes=INTERVAL_MINUTES)
    return rows


# ---------------------------------------------------------------------------
# 4. Write CSVs
# ---------------------------------------------------------------------------
def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows):,} rows -> {path}")


if __name__ == "__main__":
    # Locations
    loc_rows = [
        {"id": lid, "name": name, "type": ltype, "lat": lat, "lon": lon}
        for lid, name, ltype, lat, lon in LOCATIONS
    ]
    write_csv("locations.csv", loc_rows,
              ["id", "name", "type", "lat", "lon"])

    # Readings
    readings = generate_readings()
    write_csv("readings.csv", readings,
              ["id", "location_id", "timestamp", "congestion_level", "speed_mph", "volume"])

    print("Done generating synthetic data.")
