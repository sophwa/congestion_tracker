# City Congestion Tracker

An end-to-end AI-powered city traffic congestion monitoring system built for SYSEN 5381 Midterm (March 2026).

---

## System Architecture

```
Supabase DB  →  FastAPI REST API  →  Shiny Dashboard  →  Ollama (gpt-oss:20b-cloud)
(PostgreSQL)     (data access)        (user interface)     (AI summaries)
```

The pipeline:
1. **Supabase** stores congestion readings (15-min intervals) for 20 city locations.
2. **FastAPI** exposes those readings through a REST API with filtering by location, time window, and severity.
3. **Shiny** (Python) dashboard lets users explore current and historical congestion and request AI summaries.
4. **Ollama** receives a compact stats slice and returns a plain-language narrative for the transportation authority.

---

## Repository Structure

```
congestion_tracker/
├── data/
│   ├── generate_data.py      # Synthetic data generator (re-run to refresh data to today)
│   ├── locations.csv         # 20 monitored locations
│   └── readings.csv          # ~40,320 congestion readings (21 days, 15-min intervals, rolling window ending today)
├── database/
│   ├── schema.sql            # SQL: create tables + RLS policies (paste into Supabase SQL editor)
│   └── seed.py               # Seed script: uploads CSVs to Supabase
├── api/
│   ├── app.py                # FastAPI application
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Environment variable template
│   ├── .python-version       # Pin Python 3.12 for Posit Connect
│   └── manifest.json         # Posit Connect deployment manifest
├── dashboard/
│   ├── app.py                # Shiny (Python) dashboard
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Environment variable template
│   ├── .python-version       # Pin Python 3.12 for Posit Connect
│   └── manifest.json         # Posit Connect deployment manifest
├── tests/
│   ├── run_all_tests.sh           # Convenience wrapper: runs all tests in sequence
│   ├── test_local.py              # Offline data tests (CSV structure + model behaviour)
│   ├── test_01_locations.sh       # Live API test: list all locations
│   ├── test_02_current.sh         # Live API test: current congestion
│   ├── test_03_history.sh         # Live API test: 7-day history for one location
│   ├── test_01_expected.json      # Reference dataset: expected /locations response
│   ├── test_02_expected.json      # Reference dataset: expected /congestion/current response
│   └── test_03_expected.json      # Reference dataset: expected /congestion/history response
├── codebook.md               # Variable descriptions for all data files
└── README.md                 # This file
```

---

## Setup & Reproduction

### Prerequisites

- Python 3.12+
- A [Supabase](https://supabase.com) account (free tier is sufficient)
- An [Ollama Cloud](https://ollama.com) account with an API key and a model deployed (e.g. `gpt-oss:20b-cloud`)

### 1. Clone the repo

```bash
git clone https://github.com/sophwa/congestion_tracker.git
cd congestion_tracker
```

### 2. Create `.env` files

Both `api/` and `dashboard/` need a `.env` file. Copy the provided examples and fill in your values:

```bash
cp api/.env.example api/.env
cp dashboard/.env.example dashboard/.env
```

**`api/.env`** — fill in your Supabase project URL and anon key:
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your-anon-key
```

**`dashboard/.env`** — fill in your API URL and Ollama Cloud credentials:
```
API_BASE_URL=http://localhost:8000
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_MODEL=gpt-oss:20b-cloud
OLLAMA_API_KEY=your-ollama-cloud-api-key
```

### 3. Set up the Supabase database

1. Open the Supabase SQL editor for your project.
2. Paste the contents of `database/schema.sql` and run it.
3. The tables `locations` and `congestion_readings` are now created with public read access.

### 4. Seed synthetic data

The CSV data files are already included in the repo (`data/locations.csv` and `data/readings.csv`), pre-generated with a rolling 21-day window ending today. To refresh the data window before seeding:

```bash
# Optional: regenerate readings.csv so END = today
python3 data/generate_data.py
```

Then upload to Supabase:

```bash
pip3 install supabase python-dotenv
# Use your service-role key in api/.env for this step, then switch back to the anon key
python3 database/seed.py
```

### 5. Run the API locally

```bash
cd api
pip3 install -r requirements.txt
uvicorn app:app --reload --port 8000
# → http://localhost:8000/docs  (interactive Swagger UI)
```

### 6. Run the dashboard locally

```bash
cd dashboard
pip3 install -r requirements.txt
shiny run app.py --port 8001
# → http://localhost:8001
```

---

## REST API Reference

| Method | Endpoint | Parameters | Description |
|--------|----------|-----------|-------------|
| GET | `/` | — | Health check |
| GET | `/locations` | — | All 20 monitored locations |
| GET | `/congestion/current` | `window_minutes` (default 30) | Latest reading per location |
| GET | `/congestion/history` | `location_id`, `days` (1–30), `limit` | Time-series for one location |
| GET | `/congestion/worst` | `top_k` (default 5), `window_minutes` | Top-K most congested now |
| GET | `/congestion/summary_data` | `days` (1–30) | Aggregated stats for AI prompt |

Full interactive docs at `/docs` (Swagger UI) or `/redoc`.

---

## Dashboard Features

- **Current Congestion Table** — sortable table of all locations' latest readings, colour-coded by severity (green/orange/red)
- **Worst Locations Panel** — ranked cards for the top-K most congested locations
- **Time-Series Chart** — interactive 15-min interval line chart for any location over 1–14 days
- **AI Summary** — one click sends a compact stats slice to Ollama and displays a plain-language report covering:
  - Which areas are worst right now
  - How current conditions compare to the historical average
  - An actionable recommendation (routes to avoid, areas to monitor)

---

## Deployment (Posit Connect)

Both components have a `manifest.json` for Posit Connect deployment. Each directory contains a `.python-version` file pinning Python 3.12 to match the server environment.

```bash
# API (FastAPI)
cd api
pip3 install rsconnect-python
rsconnect deploy fastapi --server https://connect.systems-apps.com --api-key YOUR_KEY .

# Dashboard (Shiny Python)
cd dashboard
rsconnect deploy shiny --server https://connect.systems-apps.com --api-key YOUR_KEY .
```

After deploying:
1. **Set environment variables** in the Connect UI (Content → Settings → Environment Variables) for each app — see `.env.example` in each directory.
2. **Set access** to "Anyone — no login required" (Content → Settings → Access) so the API can be reached without authentication.

To regenerate the `manifest.json` files locally (e.g. after adding dependencies):

```bash
bash api/manifestme.sh
bash dashboard/manifestme.sh
```

---

## Test Examples

The `tests/` directory contains two complementary test suites:

### Offline data tests (no API needed)

Validates the CSV files and congestion model directly:

```bash
python3 tests/test_local.py
```

| # | Test | What it checks |
|---|------|----------------|
| 1 | Locations: correct count | 20 rows in `locations.csv` |
| 2 | Locations: schema | All required columns present |
| 3 | Locations: valid types | Only `intersection`, `segment`, `zone` |
| 4 | Readings: correct count | ~40,320 rows (21-day rolling window) |
| 5 | Readings: schema | All 6 required columns present |
| 6 | Readings: congestion range | All values in [0, 10] |
| 7 | Readings: speed range | All values in [5, 45] mph |
| 8 | Readings: location IDs | Only IDs 1–20 present |
| 9 | Readings: timestamp format | `YYYY-MM-DD HH:MM:SS` throughout |
| 10 | Model: peak vs night | AM peak avg > overnight avg |
| 11 | Model: weekday vs weekend | Weekday avg > weekend avg |

### Live API tests

Run against the local or deployed API. Start the API first, then:

```bash
bash tests/run_all_tests.sh                              # local
API_BASE=https://connect.systems-apps.com/content/0cfe1060-3483-462a-9f2b-478fe980a128 bash tests/run_all_tests.sh  # deployed
```

| # | Script | What it checks |
|---|--------|----------------|
| 1 | `test_01_locations.sh` | HTTP 200, 20 locations, correct schema |
| 2 | `test_02_current.sh` | HTTP 200, all `congestion_level` in [0, 10] |
| 3 | `test_03_history.sh` | HTTP 200, ascending timestamps, all `location_id == 1` |

Reference datasets for each test are in `test_01_expected.json`, `test_02_expected.json`, and `test_03_expected.json`.

---

## Data Sources

All data is **synthetic**. The `data/generate_data.py` script generates realistic congestion patterns with:
- AM peak (7–9 AM): 2× normal congestion
- PM peak (4–6 PM): 2.2× normal congestion
- Weekend reduction: 25–50% lower
- Gaussian noise for natural variation

Dates are computed **relative to today** each time the script runs, so the 21-day window always ends at the current date. Re-running the script and re-seeding Supabase keeps the "current congestion" endpoint populated with fresh data.

See `codebook.md` for full variable descriptions.