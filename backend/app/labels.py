"""Market value labels (the regression target).

API-Football has no market valuation endpoint on any plan, so labels must come
from somewhere else:

* ``csv``       - real valuations you supply in data/market_values.csv, e.g. exported
                  from the public Transfermarkt dataset on Kaggle ("player-scores").
                  Required columns: player_name, market_value_eur. Optional: season.
* ``synthetic`` - a deterministic, documented formula (+ noise) so the whole
                  pipeline works end-to-end. Demo only: the model then learns the
                  formula, not the real transfer market.
"""
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from .features import FULL_SEASON_MINUTES, TARGET

POSITION_BASE_LOG_EUR = {"Goalkeeper": 15.7, "Defender": 16.2, "Midfielder": 16.45, "Attacker": 16.6}


def synthetic_market_values(df: pd.DataFrame, seed: int = 42) -> pd.Series:
    rng = np.random.default_rng(seed)
    base = df["position"].map(POSITION_BASE_LOG_EUR).fillna(16.2)
    age_effect = -0.011 * (df["age"].astype(float) - 25) ** 2
    minutes_effect = 1.3 * np.sqrt((df["minutes"] / FULL_SEASON_MINUTES).clip(0, 1)) - 0.75
    output_effect = 0.045 * df["goals"] + 0.035 * df["assists"]
    # Persistent per-player "reputation" so a player's seasons are correlated.
    reputation = df["player_id"].map(lambda pid: np.random.default_rng(seed + int(pid)).normal(0, 0.25))
    noise = rng.normal(0, 0.3, len(df))
    value = np.exp(base + age_effect + minutes_effect + output_effect + reputation + noise)
    return (value.clip(150_000, 200_000_000) / 100_000).round() * 100_000


def normalize_name(name) -> str:
    text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", text.lower())).strip()


def _abbreviated(key: str) -> str:
    """'mohamed salah' -> 'm salah' (API-Football often uses 'M. Salah')."""
    parts = key.split()
    return f"{parts[0][0]} {' '.join(parts[1:])}" if len(parts) > 1 else key


def merge_csv_market_values(df: pd.DataFrame, csv_path: Path) -> pd.DataFrame:
    mv = pd.read_csv(csv_path)
    missing = {"player_name", "market_value_eur"} - set(mv.columns)
    if missing:
        raise ValueError(f"{csv_path.name} is missing columns: {sorted(missing)}")

    mv = mv.dropna(subset=["player_name", "market_value_eur"]).copy()
    mv["market_value_eur"] = pd.to_numeric(mv["market_value_eur"], errors="coerce")
    mv["key"] = mv["player_name"].map(normalize_name)
    has_season = "season" in mv.columns

    lookups: list[tuple[dict, bool]] = []  # (mapping, keyed_by_season)
    for key_fn in (lambda k: k, _abbreviated):
        keyed = mv.assign(key=mv["key"].map(key_fn))
        if has_season:
            seasonal = keyed.dropna(subset=["season"]).astype({"season": int})
            lookups.append((seasonal.groupby(["key", "season"])["market_value_eur"].max().to_dict(), True))
        latest_first = keyed.sort_values("season") if has_season else keyed
        lookups.append((latest_first.groupby("key")["market_value_eur"].last().to_dict(), False))

    out = df.copy()
    candidates = [
        out["name"].map(normalize_name),
        (out["firstname"].fillna("") + " " + out["lastname"].fillna("")).map(normalize_name),
    ]
    values = pd.Series(np.nan, index=out.index)
    for mapping, by_season in lookups:
        for keys in candidates:
            lookup_keys = list(zip(keys, out["season"])) if by_season else list(keys)
            found = pd.Series([mapping.get(k) for k in lookup_keys], index=out.index, dtype=float)
            values = values.fillna(found)

    out[TARGET] = values
    matched = int(values.notna().sum())
    print(f"[labels] matched {matched}/{len(out)} player-seasons from {csv_path.name}")
    if matched == 0:
        raise ValueError("No players matched market_values.csv - check the player_name format.")
    return out.dropna(subset=[TARGET])


def attach_labels(df: pd.DataFrame, mode: str, csv_path: Path) -> tuple[pd.DataFrame, str]:
    if mode not in {"auto", "csv", "synthetic"}:
        raise ValueError(f"LABEL_MODE must be auto, csv or synthetic (got {mode!r})")
    if mode == "csv" or (mode == "auto" and csv_path.exists()):
        if not csv_path.exists():
            raise FileNotFoundError(f"LABEL_MODE=csv but {csv_path} does not exist")
        return merge_csv_market_values(df, csv_path), "csv"
    out = df.copy()
    out[TARGET] = synthetic_market_values(out)
    return out, "synthetic"
