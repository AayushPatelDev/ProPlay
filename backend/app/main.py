"""ProPlay FastAPI server.

Run (from backend/):  uvicorn app.main:app --reload --port 8000
Docs:                 http://127.0.0.1:8000/docs
"""
import json
from contextlib import asynccontextmanager
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from . import config
from .features import BASE_FEATURES, TARGET, build_feature_frame, latest_season_per_player
from .labels import normalize_name

Position = Literal["Goalkeeper", "Defender", "Midfielder", "Attacker"]
state: dict = {}


def load_state() -> None:
    state.clear()
    missing = [p.name for p in (config.MODEL_PATH, config.METRICS_PATH, config.PREDICTIONS_PATH, config.DATASET_PATH)
               if not p.exists()]
    if missing:
        state["error"] = f"Missing {', '.join(missing)}. Run `python -m app.fetch_data` then `python -m app.train`."
        return
    dataset = pd.read_csv(config.DATASET_PATH)
    latest = latest_season_per_player(dataset)
    latest["search_key"] = latest["name"].map(normalize_name)
    state.update(
        model=joblib.load(config.MODEL_PATH),
        metrics=json.loads(config.METRICS_PATH.read_text()),
        predictions=pd.read_csv(config.PREDICTIONS_PATH),
        dataset=dataset,
        latest=latest.set_index("player_id", drop=False),
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_state()
    yield


app = FastAPI(title="ProPlay API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.mount("/plots", StaticFiles(directory=config.PLOTS_DIR), name="plots")


def require_model() -> None:
    if "error" in state:
        raise HTTPException(status_code=503, detail=state["error"])


def _clean(value):
    return None if pd.isna(value) else (value.item() if hasattr(value, "item") else value)


def player_summary(row: pd.Series) -> dict:
    return {
        "id": int(row["player_id"]),
        "name": row["name"],
        "team": _clean(row["team"]),
        "position": row["position"],
        "season": int(row["season"]),
        "photo": _clean(row.get("photo")) or None,
    }


class PredictRequest(BaseModel):
    """Either pass `player_id` (optionally overriding some stats) or all five stats."""
    player_id: int | None = None
    goals: int | None = Field(None, ge=0, le=80)
    assists: int | None = Field(None, ge=0, le=60)
    minutes: int | None = Field(None, ge=0, le=4000)
    age: int | None = Field(None, ge=15, le=45)
    position: Position | None = None

    @model_validator(mode="after")
    def check_inputs(self):
        if self.player_id is None and any(getattr(self, f) is None for f in BASE_FEATURES):
            raise ValueError(f"Provide player_id or all of: {', '.join(BASE_FEATURES)}")
        return self


@app.get("/api/health")
def health():
    return {"status": "ok" if "error" not in state else "untrained", "detail": state.get("error")}


@app.post("/api/reload")
def reload_artifacts():
    """Reload model + data after re-training without restarting the server."""
    load_state()
    return health()


@app.get("/api/players")
def search_players(q: str = "", limit: int = Query(20, ge=1, le=100)):
    require_model()
    latest = state["latest"]
    if q.strip():
        needle = normalize_name(q)
        latest = latest[latest["search_key"].str.contains(needle, regex=False)]
    latest = latest.sort_values(["season", "minutes"], ascending=False).head(limit)
    return {"players": [player_summary(row) for _, row in latest.iterrows()]}


@app.get("/api/players/{player_id}")
def get_player(player_id: int):
    require_model()
    if player_id not in state["latest"].index:
        raise HTTPException(status_code=404, detail="Player not found")
    row = state["latest"].loc[player_id]
    history = state["dataset"][state["dataset"]["player_id"] == player_id].sort_values("season")
    return {
        **player_summary(row),
        "nationality": _clean(row["nationality"]),
        "stats": {f: _clean(row[f]) for f in BASE_FEATURES},
        "appearances": int(row["appearances"]),
        "actual_value_eur": _clean(row[TARGET]),
        "career": {k: int(row[k]) for k in ("seasons_played", "career_goals", "career_assists", "career_minutes")},
        "history": [
            {k: _clean(h[k]) for k in ("season", "team", "age", "appearances", "minutes", "goals", "assists", TARGET)}
            for _, h in history.iterrows()
        ],
    }


@app.post("/api/predict")
def predict(req: PredictRequest):
    require_model()
    stats, player = {}, None
    if req.player_id is not None:
        if req.player_id not in state["latest"].index:
            raise HTTPException(status_code=404, detail="Player not found")
        player = state["latest"].loc[req.player_id]
        stats = {f: _clean(player[f]) for f in BASE_FEATURES}
    stats.update({f: getattr(req, f) for f in BASE_FEATURES if getattr(req, f) is not None})

    predicted = float(max(state["model"].predict(build_feature_frame(stats))[0], 0))
    metrics = state["metrics"]
    return {
        "player": player_summary(player) if player is not None else None,
        "inputs": stats,
        "predicted_value_eur": round(predicted, -4),
        "actual_value_eur": _clean(player[TARGET]) if player is not None else None,
        "currency": "EUR",
        "label_source": metrics["label_source"],
        "metrics": {"test": metrics["test"], "cv": metrics["cv"]},
    }


@app.get("/api/metrics")
def get_metrics():
    require_model()
    return state["metrics"]


@app.get("/api/evaluation")
def evaluation():
    """Out-of-fold actual vs predicted values for every training row."""
    require_model()
    cols = ["player_id", "name", "team", "season", "position", "actual", "predicted", "split"]
    points = state["predictions"][cols].astype(object).where(state["predictions"][cols].notna(), None)
    return {"points": points.to_dict(orient="records"), "trained_at": state["metrics"]["trained_at"]}
