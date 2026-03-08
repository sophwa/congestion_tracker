# app.py
# City Congestion Tracker — Shiny Dashboard (Python)
# Deployed to Posit Connect.
#
# Pipeline: Supabase → FastAPI → this dashboard → Ollama
#
# The dashboard:
#   - calls the REST API for current and historical congestion data
#   - renders an interactive table and time-series chart
#   - sends a compact stats slice to Ollama for a plain-language AI summary
#
# Environment variables (.env):
#   API_BASE_URL    = https://your-api.example.com   (the FastAPI deployment URL)
#   OLLAMA_BASE_URL = http://localhost:11434          (local) or your Ollama Cloud URL
#   OLLAMA_MODEL    = llama3.2                        (any model pulled in Ollama)
#   OLLAMA_API_KEY  = (optional, only for cloud deployments that require auth)

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

from shiny import reactive, render, ui
from shiny.express import input, ui as xui

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_ = load_dotenv()

API_BASE    = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "https://ollama.com").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud")
OLLAMA_KEY  = os.getenv("OLLAMA_API_KEY", "")   # optional; required by some cloud hosts

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def api_get(path: str, params: dict = None):
    """Call the REST API and return parsed JSON, or an empty list on error."""
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return []


def congestion_color(level: float) -> str:
    if level >= 7:
        return "red"
    if level >= 4:
        return "orange"
    return "green"


def congestion_label(level: float) -> str:
    if level >= 7:
        return "High"
    if level >= 4:
        return "Moderate"
    return "Low"


# ---------------------------------------------------------------------------
# AI summary helper
# ---------------------------------------------------------------------------
def call_ollama(prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    if OLLAMA_KEY:
        headers["Authorization"] = f"Bearer {OLLAMA_KEY}"
    body = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    try:
        r = requests.post(f"{OLLAMA_BASE}/api/chat", headers=headers, json=body, timeout=60)
        r.raise_for_status()
        result = r.json()
        return result["message"]["content"]
    except Exception as e:
        return f"AI summary error: {e}"


def build_ai_prompt(current: list, summary_stats: list, days: int) -> str:
    """Construct the prompt sent to OpenAI."""
    # Top 5 worst right now
    top5 = sorted(current, key=lambda x: x.get(
        "congestion_level", 0), reverse=True)[:5]
    top5_lines = "\n".join(
        f"  - {r.get('location_name', r['location_id'])}: "
        f"{r['congestion_level']:.1f}/10 ({r.get('speed_mph', '?')} mph)"
        for r in top5
    )

    # Overall stats
    if summary_stats:
        avg_all = sum(s["avg_congestion"]
                      for s in summary_stats) / len(summary_stats)
        worst_hist = max(summary_stats, key=lambda s: s["avg_congestion"])
    else:
        avg_all = 0
        worst_hist = None

    hist_line = (
        f"{worst_hist['location_name']} ({worst_hist['avg_congestion']:.1f} avg)"
        if worst_hist else "N/A"
    )

    prompt = f"""You are a city traffic analyst. Based on the congestion data below, write a concise (4–6 sentence) plain-language summary for a transportation authority dashboard. Cover: (1) which areas are worst right now, (2) how current conditions compare to the {days}-day average, and (3) one actionable recommendation (e.g., which roads to avoid or monitor next).

CURRENT TOP 5 CONGESTED LOCATIONS (now):
{top5_lines}

{days}-DAY HISTORICAL AVERAGES:
  - Overall network average congestion: {avg_all:.2f}/10
  - Historically busiest location: {hist_line}
  - Locations monitored: {len(summary_stats)}

Keep the summary short, direct, and useful for a non-technical audience.
"""
    return prompt


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
xui.page_opts(title="City Congestion Tracker", fillable=True)

with xui.sidebar(open="desktop", width=280):
    xui.h5("Controls")
    xui.input_select(
        "view_days",
        "History window (days)",
        choices={"1": "1 day", "3": "3 days", "7": "7 days", "14": "14 days"},
        selected="7",
    )
    xui.input_select(
        "top_k",
        "Worst locations to highlight",
        choices={"3": "Top 3", "5": "Top 5", "10": "Top 10"},
        selected="5",
    )
    xui.input_select(
        "location_id",
        "Location for time-series chart",
        choices={},   # populated reactively
    )
    xui.input_action_button("refresh", "Refresh data",
                            class_="btn-primary w-100 mt-2")
    xui.input_action_button("summarise", "Get AI summary",
                            class_="btn-success w-100 mt-2")
    xui.hr()
    xui.p(xui.tags.small(
        "Data updates every 15 minutes. Click 'Refresh data' to reload."
    ))

with xui.layout_columns(col_widths=[6, 6]):
    with xui.card(full_screen=True):
        xui.card_header("Current Congestion (all locations)")

        @render.data_frame
        def current_table():
            _ = input.refresh()  # dependency
            rows = api_get("/congestion/current", {"window_minutes": 30})
            if not rows:
                return None
            import pandas as pd
            df = pd.DataFrame([{
                "Location":    r.get("location_name", r["location_id"]),
                "Level (0-10)": r["congestion_level"],
                "Status":      congestion_label(r["congestion_level"]),
                "Speed (mph)": r.get("speed_mph", ""),
                "Volume":      r.get("volume", ""),
                "Timestamp":   r["timestamp"][:16].replace("T", " "),
            } for r in rows])
            df = df.sort_values(
                "Level (0-10)", ascending=False).reset_index(drop=True)
            return render.DataGrid(df, selection_mode="none")

    with xui.card(full_screen=True):
        xui.card_header("Worst Locations Right Now")

        @render.ui
        def worst_cards():
            _ = input.refresh()
            k = int(input.top_k())
            rows = api_get("/congestion/worst",
                           {"top_k": k, "window_minutes": 30})
            if not rows:
                return xui.p("No data available.")
            cards = []
            for i, r in enumerate(rows, 1):
                color = congestion_color(r["congestion_level"])
                label = congestion_label(r["congestion_level"])
                cards.append(
                    xui.div(
                        xui.strong(
                            f"#{i} {r.get('location_name', r['location_id'])}"),
                        xui.br(),
                        xui.span(
                            f"{r['congestion_level']:.1f}/10 — {label}",
                            style=f"color:{color}; font-weight:bold",
                        ),
                        xui.br(),
                        xui.tags.small(
                            f"Speed: {r.get('speed_mph', '?')} mph | Vol: {r.get('volume', '?')}"),
                        class_="mb-2 p-2 border rounded",
                    )
                )
            return xui.div(*cards)

with xui.card(full_screen=True):
    xui.card_header("Time-Series: Congestion Over Time")

    @render.plot
    def history_plot():
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        _ = input.refresh()
        loc_id_str = input.location_id()
        days = int(input.view_days())

        if not loc_id_str:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "Select a location", ha="center", va="center")
            return fig

        rows = api_get("/congestion/history",
                       {"location_id": int(loc_id_str), "days": days, "limit": 2000})
        if not rows:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No data for this location/window",
                    ha="center", va="center")
            return fig

        timestamps = [datetime.fromisoformat(
            r["timestamp"].replace("Z", "+00:00")) for r in rows]
        levels = [r["congestion_level"] for r in rows]
        loc_name = rows[0].get("location_name", loc_id_str)

        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.plot(timestamps, levels, linewidth=1, color="#2563EB")
        ax.fill_between(timestamps, levels, alpha=0.15, color="#2563EB")
        ax.axhline(7, color="red",    linestyle="--",
                   linewidth=0.8, label="High (7)")
        ax.axhline(4, color="orange", linestyle="--",
                   linewidth=0.8, label="Moderate (4)")
        ax.set_ylabel("Congestion Level (0–10)")
        ax.set_title(f"{loc_name} — last {days} day(s)")
        ax.set_ylim(0, 10)
        ax.legend(fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        fig.autofmt_xdate(rotation=30)
        fig.tight_layout()
        return fig

with xui.card():
    xui.card_header("AI Summary")

    @render.ui
    def ai_summary():
        _ = input.summarise()  # only runs when button clicked
        if input.summarise() == 0:
            return xui.p("Click 'Get AI summary' to generate an Ollama-powered insight.",
                         style="color: gray;")

        days = int(input.view_days())
        current = api_get("/congestion/current", {"window_minutes": 30})
        summary_stats = api_get("/congestion/summary_data", {"days": days})

        prompt = build_ai_prompt(current, summary_stats, days)
        text = call_ollama(prompt)

        return xui.div(
            xui.p(text),
            xui.tags.small(
                f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC | "
                f"Model: {OLLAMA_MODEL}",
                style="color: gray;",
            ),
        )

# ---------------------------------------------------------------------------
# Reactive: populate location dropdown from API
# ---------------------------------------------------------------------------


@reactive.effect
def _populate_locations():
    _ = input.refresh()
    locs = api_get("/locations")
    choices = {str(l["id"]): l["name"]
               for l in locs} if locs else {"1": "Location 1"}
    ui.update_select("location_id", choices=choices,
                     selected=list(choices.keys())[0])
