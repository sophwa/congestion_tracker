-- schema.sql
-- City Congestion Tracker - Supabase PostgreSQL Schema
-- Run this in the Supabase SQL editor to create the required tables.

-- ============================================================
-- Table: locations
-- One row per monitored location (intersection, segment, zone)
-- ============================================================
CREATE TABLE IF NOT EXISTS locations (
    id      SERIAL PRIMARY KEY,
    name    TEXT    NOT NULL,          -- human-readable label
    type    TEXT    NOT NULL           -- 'intersection' | 'segment' | 'zone'
        CHECK (type IN ('intersection', 'segment', 'zone')),
    lat     DOUBLE PRECISION,          -- latitude (WGS-84)
    lon     DOUBLE PRECISION           -- longitude (WGS-84)
);

-- ============================================================
-- Table: congestion_readings
-- One row per 15-minute observation at a location
-- ============================================================
CREATE TABLE IF NOT EXISTS congestion_readings (
    id                BIGSERIAL PRIMARY KEY,
    location_id       INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    timestamp         TIMESTAMPTZ NOT NULL,       -- UTC observation time
    congestion_level  NUMERIC(4,2) NOT NULL       -- 0 (free flow) to 10 (gridlock)
        CHECK (congestion_level >= 0 AND congestion_level <= 10),
    speed_mph         NUMERIC(5,1),               -- estimated speed in mph
    volume            INTEGER                     -- vehicles per 15-min interval
);

-- Index for fast time-range queries
CREATE INDEX IF NOT EXISTS idx_readings_location_time
    ON congestion_readings (location_id, timestamp DESC);

-- Index for sorting by timestamp across all locations
CREATE INDEX IF NOT EXISTS idx_readings_time
    ON congestion_readings (timestamp DESC);

-- ============================================================
-- Row-Level Security (Supabase)
-- Allow anonymous read access so the API can query without auth
-- ============================================================
ALTER TABLE locations          ENABLE ROW LEVEL SECURITY;
ALTER TABLE congestion_readings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read locations"
    ON locations FOR SELECT USING (true);

CREATE POLICY "Public read readings"
    ON congestion_readings FOR SELECT USING (true);