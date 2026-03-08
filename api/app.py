# app.py
# City Congestion Tracker — REST API
# Built with FastAPI; deployed to Posit Connect or DigitalOcean.
#
# Pipeline: Supabase → this API → Shiny dashboard → OpenAI
#
# Endpoints:
#   GET /locations                     list all monitored locations
#   GET /congestion/current            latest reading per location (last 30 min)
#   GET /congestion/history            readings for a location over N days
#   GET /congestion/worst              top-K most congested locations right now
#   GET /congestion/summary_data       compact stats slice for AI summarisation
#
# Environment variables (.env):
#   SUPABASE_URL  = https://xxxx.supabase.co
#   SUPABASE_KEY  = your-anon-key   (read-only anon key is fine)

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(
    title="City Congestion Tracker API",
    description=(
        "REST API exposing city traffic congestion data stored in Supabase. "
        "Supports current readings, historical queries, and summary slices for AI."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class Location(BaseModel):
    id: int
    name: str
    type: str
    lat: Optional[float]
    lon: Optional[float]


class Reading(BaseModel):
    id: int
    location_id: int
    location_name: Optional[str]
    timestamp: str
    congestion_level: float
    speed_mph: Optional[float]
    volume: Optional[int]


class SummaryStats(BaseModel):
    location_id: int
    location_name: str
    location_type: str
    avg_congestion: float
    max_congestion: float
    min_congestion: float
    reading_count: int
    window_start: str
    window_end: str


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
def root():
    """Health-check / welcome endpoint."""
    return {
        "service": "City Congestion Tracker API",
        "version": "1.0.0",
        "status": "ok",
        "timestamp": iso(utc_now()),
    }


@app.get("/locations", response_model=list[Location], tags=["Locations"])
def get_locations():
    """Return all monitored locations (intersections, segments, zones)."""
    resp = supabase.table("locations").select("*").order("id").execute()
    return resp.data


@app.get("/congestion/current", response_model=list[Reading], tags=["Congestion"])
def get_current_congestion(
    window_minutes: int = Query(30, ge=5, le=120,
                                description="How many minutes back to look for 'current' readings"),
):
    """
    Return the most-recent reading per location within the last `window_minutes`.

    Because the database stores 15-min intervals, using window_minutes=30
    guarantees at least one reading per location is included.
    """
    since = iso(utc_now() - timedelta(minutes=window_minutes))

    resp = (
        supabase.table("congestion_readings")
        .select("*, locations(name)")
        .gte("timestamp", since)
        .order("timestamp", desc=True)
        .execute()
    )

    # Keep only the latest reading per location
    seen = set()
    result = []
    for row in resp.data:
        lid = row["location_id"]
        if lid not in seen:
            seen.add(lid)
            result.append({
                "id":               row["id"],
                "location_id":      lid,
                "location_name":    row.get("locations", {}).get("name") if row.get("locations") else None,
                "timestamp":        row["timestamp"],
                "congestion_level": float(row["congestion_level"]),
                "speed_mph":        float(row["speed_mph"]) if row.get("speed_mph") is not None else None,
                "volume":           row.get("volume"),
            })
    return result


@app.get("/congestion/history", response_model=list[Reading], tags=["Congestion"])
def get_history(
    location_id: int = Query(..., description="Location ID to query"),
    days: int = Query(
        7, ge=1, le=30, description="Number of past days to include"),
    limit: int = Query(500, ge=1, le=5000,
                       description="Maximum rows returned"),
):
    """
    Return time-series readings for a single location over the past `days` days.
    Results are ordered oldest-first for charting.
    """
    since = iso(utc_now() - timedelta(days=days))

    # Verify location exists
    loc_resp = supabase.table("locations").select(
        "*").eq("id", location_id).execute()
    if not loc_resp.data:
        raise HTTPException(
            status_code=404, detail=f"Location {location_id} not found")

    loc_name = loc_resp.data[0]["name"]

    resp = (
        supabase.table("congestion_readings")
        .select("*")
        .eq("location_id", location_id)
        .gte("timestamp", since)
        .order("timestamp", desc=False)
        .limit(limit)
        .execute()
    )

    return [
        {
            "id":               row["id"],
            "location_id":      row["location_id"],
            "location_name":    loc_name,
            "timestamp":        row["timestamp"],
            "congestion_level": float(row["congestion_level"]),
            "speed_mph":        float(row["speed_mph"]) if row.get("speed_mph") is not None else None,
            "volume":           row.get("volume"),
        }
        for row in resp.data
    ]


@app.get("/congestion/worst", response_model=list[Reading], tags=["Congestion"])
def get_worst(
    top_k: int = Query(5, ge=1, le=20,
                       description="Number of worst locations to return"),
    window_minutes: int = Query(30, ge=5, le=120,
                                description="Recency window for 'current' readings"),
):
    """
    Return the top-K locations with the highest current congestion level.
    """
    since = iso(utc_now() - timedelta(minutes=window_minutes))

    resp = (
        supabase.table("congestion_readings")
        .select("*, locations(name)")
        .gte("timestamp", since)
        .order("congestion_level", desc=True)
        .execute()
    )

    seen = set()
    result = []
    for row in resp.data:
        if len(result) >= top_k:
            break
        lid = row["location_id"]
        if lid not in seen:
            seen.add(lid)
            result.append({
                "id":               row["id"],
                "location_id":      lid,
                "location_name":    row.get("locations", {}).get("name") if row.get("locations") else None,
                "timestamp":        row["timestamp"],
                "congestion_level": float(row["congestion_level"]),
                "speed_mph":        float(row["speed_mph"]) if row.get("speed_mph") is not None else None,
                "volume":           row.get("volume"),
            })
    return result


@app.get("/congestion/summary_data", response_model=list[SummaryStats], tags=["Congestion"])
def get_summary_data(
    days: int = Query(7, ge=1, le=30,
                      description="Number of past days to aggregate"),
):
    """
    Return aggregated congestion statistics per location over the past `days` days.
    This compact payload is designed to be fed directly to an AI model for
    narrative summarisation.
    """
    since = iso(utc_now() - timedelta(days=days))
    now = iso(utc_now())

    # Pull all readings in window
    resp = (
        supabase.table("congestion_readings")
        .select("location_id, congestion_level, locations(name, type)")
        .gte("timestamp", since)
        .execute()
    )

    # Aggregate in Python (Supabase free tier doesn't expose aggregate RPC)
    from collections import defaultdict
    stats: dict[int, dict] = defaultdict(lambda: {
        "values": [], "name": "", "type": ""
    })
    for row in resp.data:
        lid = row["location_id"]
        stats[lid]["values"].append(float(row["congestion_level"]))
        if row.get("locations"):
            stats[lid]["name"] = row["locations"]["name"]
            stats[lid]["type"] = row["locations"]["type"]

    result = []
    for lid, data in sorted(stats.items()):
        vals = data["values"]
        if not vals:
            continue
        result.append({
            "location_id":    lid,
            "location_name":  data["name"],
            "location_type":  data["type"],
            "avg_congestion": round(sum(vals) / len(vals), 2),
            "max_congestion": round(max(vals), 2),
            "min_congestion": round(min(vals), 2),
            "reading_count":  len(vals),
            "window_start":   since,
            "window_end":     now,
        })
    return result
