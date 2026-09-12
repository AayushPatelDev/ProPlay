"""Central configuration. Values come from backend/.env (see .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _csv_env(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# --- API-Football -----------------------------------------------------------
API_KEY = os.getenv("API_KEY", "").strip()
API_BASE_URL = os.getenv("API_BASE_URL", "https://v3.football.api-sports.io").rstrip("/")
LEAGUE_ID = int(os.getenv("LEAGUE_ID", "39"))
SEASONS = [int(s) for s in _csv_env("SEASONS", "2021,2022,2023")]
REQUEST_INTERVAL_SECONDS = float(os.getenv("REQUEST_INTERVAL_SECONDS", "6.5"))
# Free plan rejects page > 3, so players are fetched per club (a squad fits in 2-3 pages).
MAX_PAGES_PER_QUERY = int(os.getenv("MAX_PAGES_PER_QUERY", "3"))

# --- Labels -----------------------------------------------------------------
LABEL_MODE = os.getenv("LABEL_MODE", "auto").strip().lower()

# --- Server -----------------------------------------------------------------
CORS_ORIGINS = _csv_env("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

# --- Paths ------------------------------------------------------------------
DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"
PLOTS_DIR = ARTIFACTS_DIR / "plots"

DATASET_PATH = PROCESSED_DIR / "player_seasons.csv"
DATASET_META_PATH = PROCESSED_DIR / "dataset_meta.json"
MARKET_VALUES_CSV = DATA_DIR / "market_values.csv"

MODEL_PATH = ARTIFACTS_DIR / "model.joblib"  # full sklearn pipeline (local only)
MODEL_SPEC_PATH = ARTIFACTS_DIR / "model.json"  # sklearn-free export the API serves
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"
PREDICTIONS_PATH = ARTIFACTS_DIR / "predictions.csv"

for _dir in (RAW_DIR, PROCESSED_DIR, PLOTS_DIR):
    try:
        _dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # read-only filesystem (e.g. Vercel functions): serving needs no writes
