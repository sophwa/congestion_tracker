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
│   ├── generate_data.py      # Synthetic data generator (run once)
│   ├── locations.csv         # 20 monitored locations
│   └── readings.csv          # ~26,880 congestion readings (14 days, 15-min intervals)
├── database/
│   ├── schema.sql            # SQL: create tables + RLS policies (paste into Supabase SQL editor)
│   └── seed.py               # Seed script: uploads CSVs to Supabase
├── api/
│   ├── app.py                # FastAPI application
│   ├── requirements.txt      # Python dependencies
│   └── manifest.json         # Posit Connect deployment manifest
├── dashboard/
│   ├── app.py                # Shiny (Python) dashboard
│   ├── requirements.txt      # Python dependencies
│   └── manifest.json         # Posit Connect deployment manifest
├── tests/
│   ├── test_01_locations.sh       # Test: list all locations
│   ├── test_02_current.sh         # Test: current congestion
│   ├── test_03_history.sh         # Test: 7-day history for one location
│   ├── test_01_expected.json      # Expected output (locations)
│   ├── test_02_expected.json      # Expected output (current)
│   └── test_03_expected.json      # Expected output (history)
├── codebook.md               # Variable descriptions for all data files
└── README.md                 # This file
```

---

## Setup & Reproduction

### Prerequisites

- Python 3.11+
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
OLLAMA_BASE_URL=https://your-ollama-cloud-host
OLLAMA_MODEL=gpt-oss:20b-cloud
OLLAMA_API_KEY=your-ollama-cloud-api-key
```

### 3. Set up the Supabase database

1. Open the Supabase SQL editor for your project.
2. Paste the contents of `database/schema.sql` and run it.
3. The tables `locations` and `congestion_readings` are now created with public read access.

### 4. Seed synthetic data

The CSV data files are already included in the repo (`data/locations.csv` and `data/readings.csv`). Just upload them to Supabase:

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

Both components have a `manifest.json` for Posit Connect deployment.

```bash
# API (FastAPI)
cd api
pip3 install rsconnect-python
rsconnect deploy fastapi --server https://your.posit.server --api-key YOUR_KEY .

# Dashboard (Shiny Python)
cd dashboard
rsconnect deploy shiny --server https://your.posit.server --api-key YOUR_KEY .
```

Alternatively, deploy each as a DigitalOcean App Platform service (set the run command to `uvicorn app:app --host 0.0.0.0 --port 8080` for the API and `shiny run app.py --host 0.0.0.0 --port 8080` for the dashboard).

---

## Test Examples

See `tests/` for three curl-based test scripts and their expected outputs. Quick summary:

| # | Test | What it checks |
|---|------|----------------|
| 1 | `test_01_locations.sh` | Returns 20 locations with correct schema |
| 2 | `test_02_current.sh` | Returns current readings, all levels 0–10 |
| 3 | `test_03_history.sh` | Returns ordered time-series for location 1, last 7 days |

---

## Data Sources

All data is **synthetic**. The `data/generate_data.py` script generates realistic congestion patterns with:
- AM peak (7–9 AM): 2× normal congestion
- PM peak (4–6 PM): 2.2× normal congestion
- Weekend reduction: 25–50% lower
- Gaussian noise for natural variation

See `codebook.md` for full variable descriptions.