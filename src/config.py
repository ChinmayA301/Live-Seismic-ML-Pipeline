"""Central config for the live seismic pipeline."""
from __future__ import annotations
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DB = DATA / "seismic.duckdb"
REPORTS = ROOT / "reports"
FIG = REPORTS / "figures"
MODELS = ROOT / "models"
MLRUNS = ROOT / "mlruns"

SEED = 42

# USGS real-time feeds (no auth). Cadence: ~1 min. Docs:
# https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php
FEEDS = {
    "hour": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
    "day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    "week": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson",
    "month": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson",
}

# Model: estimate cataloged magnitude from detection-network geometry.
TARGET = "mag"
FEATURES_NUM = ["depth", "nst", "gap", "dmin", "rms", "abs_lat", "lon",
                "log_nst", "log_dmin", "hour"]
FEATURES_CAT = ["net", "magType"]
PI_ALPHAS = (0.05, 0.95)          # 90% prediction interval for the QA/anomaly flag
