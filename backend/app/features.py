"""Cleaning, cross-season aggregation and feature engineering with pandas."""
from datetime import date

import numpy as np
import pandas as pd

POSITIONS = ["Goalkeeper", "Defender", "Midfielder", "Attacker"]
_POSITION_ALIASES = {
    "g": "Goalkeeper", "gk": "Goalkeeper", "goalkeeper": "Goalkeeper",
    "d": "Defender", "df": "Defender", "defender": "Defender",
    "m": "Midfielder", "mf": "Midfielder", "midfielder": "Midfielder",
    "f": "Attacker", "fw": "Attacker", "forward": "Attacker", "attacker": "Attacker",
}

# The five raw inputs the model is driven by ...
BASE_FEATURES = ["goals", "assists", "minutes", "age", "position"]
# ... and what the pipeline actually sees after engineering.
NUMERIC_FEATURES = ["goals", "assists", "minutes", "age", "age_sq", "ga_per90"]
CATEGORICAL_FEATURES = ["position"]
TARGET = "market_value_eur"

FULL_SEASON_MINUTES = 38 * 90
MIN_MINUTES_FOR_TRAINING = 90

PLAYER_COLUMNS = [
    "player_id", "name", "firstname", "lastname", "nationality", "photo",
    "team", "season", "position", "age", "appearances", "minutes", "goals", "assists",
]


def normalize_position(value) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return _POSITION_ALIASES.get(str(value).strip().lower())


def age_at_season_start(birth_date: str | None, season: int, fallback: int | None) -> int | None:
    """Age on 1 August of the season's starting year (API 'age' is *current* age)."""
    if birth_date:
        try:
            born = date.fromisoformat(birth_date[:10])
            ref = date(season, 8, 1)
            return ref.year - born.year - ((ref.month, ref.day) < (born.month, born.day))
        except ValueError:
            pass
    return fallback


def flatten_players_payload(items: list[dict], season: int, league_id: int) -> list[dict]:
    """Turn API-Football /players response items into one row per player-team."""
    rows = []
    for item in items:
        player = item.get("player") or {}
        for stat in item.get("statistics") or []:
            league = stat.get("league") or {}
            if league.get("id") not in (None, league_id):
                continue
            games = stat.get("games") or {}
            goals = stat.get("goals") or {}
            rows.append({
                "player_id": player.get("id"),
                "name": player.get("name"),
                "firstname": player.get("firstname"),
                "lastname": player.get("lastname"),
                "nationality": player.get("nationality"),
                "photo": player.get("photo"),
                "team": (stat.get("team") or {}).get("name"),
                "season": season,
                "position": games.get("position"),
                "age": age_at_season_start((player.get("birth") or {}).get("date"), season, player.get("age")),
                "appearances": games.get("appearences"),  # (sic) API spelling
                "minutes": games.get("minutes"),
                "goals": goals.get("total"),
                "assists": goals.get("assists"),
            })
    return rows


def clean_player_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Duplicate stat lines under a player's later club often have goals=None; remember that before filling.
    df["stats_reported"] = pd.to_numeric(df["goals"], errors="coerce").notna()
    for col in ("appearances", "minutes", "goals", "assists"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).clip(lower=0).astype(int)
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df["player_id"] = pd.to_numeric(df["player_id"], errors="coerce")
    df["position"] = df["position"].map(normalize_position)
    df["name"] = df["name"].astype("string").str.strip()
    df = df.dropna(subset=["player_id", "name", "position", "age"])
    df["player_id"] = df["player_id"].astype(int)
    df["age"] = df["age"].astype(int)
    df = df[df["age"].between(15, 45)]
    return df.drop_duplicates(subset=["player_id", "season", "team"], keep="last")


def drop_duplicate_stat_lines(df: pd.DataFrame) -> pd.DataFrame:
    """Remove the same season stat line reported under two clubs.

    Team-scoped /players queries also return a player's season under clubs they
    joined *later*, as an inconsistent copy: the same minutes (±5%) but different
    apps, goals=None, or a 0-minute ghost row. Genuine mid-season transfers split
    minutes between clubs, so minutes are the reliable signal.

    Which copy to keep is a heuristic (club labels can't be verified from this
    endpoint): prefer rows with goals reported, then fewer appearances. Copies
    tend to have inflated apps; this picks the right club for known cases.
    """
    order = ["stats_reported", "appearances"] if "stats_reported" in df else ["appearances"]
    df = df.sort_values(order, ascending=[False, True][-len(order):])
    keep = []
    for _, group in df.groupby(["player_id", "season"], sort=False):
        played = (group["minutes"] > 0).any()
        kept: list[pd.Series] = []
        for idx, row in group.iterrows():
            if played and row["minutes"] == 0:
                continue  # ghost row under another club
            duplicate = any(
                abs(row["minutes"] - k["minutes"]) <= max(30, 0.06 * max(row["minutes"], k["minutes"]))
                for k in kept
            )
            if not duplicate:
                kept.append(row)
                keep.append(idx)
    return df.loc[keep]


def aggregate_player_seasons(df: pd.DataFrame) -> pd.DataFrame:
    """Merge mid-season transfers into a single player-season row."""
    df = drop_duplicate_stat_lines(df)
    agg = df.groupby(["player_id", "season"], as_index=False).agg(
        name=("name", "first"),
        firstname=("firstname", "first"),
        lastname=("lastname", "first"),
        nationality=("nationality", "first"),
        photo=("photo", "first"),
        team=("team", lambda s: " / ".join(dict.fromkeys(s.dropna()))),
        position=("position", "first"),
        age=("age", "max"),
        appearances=("appearances", "sum"),
        minutes=("minutes", "sum"),
        goals=("goals", "sum"),
        assists=("assists", "sum"),
    )
    agg["minutes"] = agg["minutes"].clip(upper=FULL_SEASON_MINUTES)
    return agg.sort_values(["season", "player_id"]).reset_index(drop=True)


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive model features from the five base inputs."""
    df = df.copy()
    df["age_sq"] = (df["age"] - 26) ** 2  # value peaks mid-career, not linearly with age
    df["ga_per90"] = (df["goals"] + df["assists"]) / np.maximum(df["minutes"], 90) * 90
    return df


def build_feature_frame(stats: dict) -> pd.DataFrame:
    frame = pd.DataFrame([{k: stats[k] for k in BASE_FEATURES}])
    return add_engineered_features(frame)[NUMERIC_FEATURES + CATEGORICAL_FEATURES]


def latest_season_per_player(df: pd.DataFrame) -> pd.DataFrame:
    """Most recent season for every player, plus career totals across seasons."""
    career = df.groupby("player_id").agg(
        seasons_played=("season", "nunique"),
        career_goals=("goals", "sum"),
        career_assists=("assists", "sum"),
        career_minutes=("minutes", "sum"),
    )
    latest = df.sort_values("season").groupby("player_id").tail(1).set_index("player_id")
    return latest.join(career).reset_index()
