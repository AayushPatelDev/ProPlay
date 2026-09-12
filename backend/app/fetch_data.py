"""Ingest EPL player statistics from API-Football v3 and build the training dataset.

Usage (from backend/):
    python -m app.fetch_data              # API if API_KEY is set, otherwise mock data
    python -m app.fetch_data --mock       # force the offline mock dataset
    python -m app.fetch_data --status     # show plan + remaining daily requests
    python -m app.fetch_data --offline    # rebuild from cached pages only (0 requests)
    python -m app.fetch_data --seasons 2022 2023 --labels csv

Every API page is cached in data/raw/, so re-running never re-spends quota and an
interrupted run (e.g. daily limit hit) resumes where it stopped the next day.
"""
import argparse
import json
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from . import config
from .features import aggregate_player_seasons, clean_player_rows, flatten_players_payload
from .labels import attach_labels
from .mock_data import generate_mock_dataset


class ApiFootballError(RuntimeError):
    pass


class ApiFootballClient:
    def __init__(self, api_key: str, base_url: str = config.API_BASE_URL,
                 min_interval: float = config.REQUEST_INTERVAL_SECONDS, offline: bool = False):
        if not api_key and not offline:
            raise ApiFootballError("API_KEY is empty - add it to backend/.env")
        self.offline = offline
        self.base_url = base_url
        self.min_interval = min_interval
        self.session = requests.Session()
        self.session.headers.update({"x-apisports-key": api_key})
        self._last_request = 0.0

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        wait = self.min_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

        response = self.session.get(f"{self.base_url}/{endpoint.lstrip('/')}", params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        errors = payload.get("errors")
        if errors:  # API-Football returns HTTP 200 with an "errors" object/list
            raise ApiFootballError(json.dumps(errors))
        remaining = response.headers.get("x-ratelimit-requests-remaining")
        if remaining is not None:
            print(f"    daily requests remaining: {remaining}")
        return payload

    def status(self) -> dict:
        return self.get("status")["response"]

    def _cached_get(self, cache_name: str, endpoint: str, params: dict) -> dict:
        cache = config.RAW_DIR / cache_name
        if cache.exists():
            return json.loads(cache.read_text())
        if self.offline:
            raise ApiFootballError(f"offline: {cache.name} not cached")
        print(f"  GET /{endpoint} {params}")
        payload = self.get(endpoint, params)
        cache.write_text(json.dumps(payload))
        return payload

    def league_teams(self, league_id: int, season: int) -> list[dict]:
        payload = self._cached_get(f"teams_league{league_id}_season{season}.json", "teams",
                                   {"league": league_id, "season": season})
        return [entry["team"] for entry in payload.get("response", [])]

    def team_players_page(self, league_id: int, team_id: int, season: int, page: int) -> dict:
        return self._cached_get(f"players_league{league_id}_team{team_id}_season{season}_page{page}.json", "players",
                                {"league": league_id, "team": team_id, "season": season, "page": page})


def fetch_api_rows(client: ApiFootballClient, league_id: int, seasons: list[int]) -> list[dict]:
    """Fetch club by club (the free plan caps `page` at 3, too few for a whole league)."""
    rows: list[dict] = []
    for season in sorted(seasons, reverse=True):  # newest first, so quota goes to recent data
        print(f"Season {season}/{str(season + 1)[-2:]}")
        try:
            teams = client.league_teams(league_id, season)
            for team in teams:
                page, total = 1, 1
                try:
                    while page <= min(total, config.MAX_PAGES_PER_QUERY):
                        payload = client.team_players_page(league_id, team["id"], season, page)
                        total = (payload.get("paging") or {}).get("total", 1)
                        rows.extend(flatten_players_payload(payload.get("response", []), season, league_id))
                        page += 1
                except ApiFootballError as exc:
                    if not client.offline:
                        raise
                    if page > 1:
                        print(f"  ~ {team['name']}: partial ({page - 1} cached page(s))")
                    continue  # offline: use whatever is cached, skip the rest
                if total > config.MAX_PAGES_PER_QUERY:
                    print(f"  ! {team['name']}: only first {config.MAX_PAGES_PER_QUERY}/{total} pages allowed")
        except (ApiFootballError, requests.RequestException) as exc:
            print(f"  ! stopped during season {season}: {exc}")
            print("    Cached pages are kept; re-run later to resume.")
            if rows:
                break
            raise
        print(f"  collected {len(teams)} clubs")
    return rows


def save_dataset(df: pd.DataFrame, source: str, label_source: str) -> None:
    df.to_csv(config.DATASET_PATH, index=False)
    meta = {
        "data_source": source,
        "label_source": label_source,
        "seasons": sorted(int(s) for s in df["season"].unique()),
        "rows": int(len(df)),
        "players": int(df["player_id"].nunique()),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    config.DATASET_META_PATH.write_text(json.dumps(meta, indent=2))
    print(f"Saved {meta['rows']} player-seasons ({meta['players']} players) -> {config.DATASET_PATH}")
    print(f"data source: {source} | label source: {label_source}")


def build_mock_dataset(label_mode: str = "synthetic") -> None:
    raw = generate_mock_dataset()
    df = aggregate_player_seasons(clean_player_rows(raw))
    # Mock players are fictional, so real CSV labels can never match them.
    df, label_source = attach_labels(df, "synthetic" if label_mode == "auto" else label_mode, config.MARKET_VALUES_CSV)
    save_dataset(df, "mock", label_source)


def build_api_dataset(seasons: list[int], label_mode: str, offline: bool = False) -> None:
    client = ApiFootballClient(config.API_KEY, offline=offline)
    rows = fetch_api_rows(client, config.LEAGUE_ID, seasons)
    if not rows:
        raise ApiFootballError("API returned no player rows")
    df = aggregate_player_seasons(clean_player_rows(pd.DataFrame(rows)))
    df, label_source = attach_labels(df, label_mode, config.MARKET_VALUES_CSV)
    save_dataset(df, "api-football", label_source)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mock", action="store_true", help="use the offline mock dataset")
    parser.add_argument("--status", action="store_true", help="print API plan/quota and exit")
    parser.add_argument("--seasons", type=int, nargs="+", default=config.SEASONS)
    parser.add_argument("--labels", choices=["auto", "csv", "synthetic"], default=config.LABEL_MODE)
    parser.add_argument("--no-fallback", action="store_true", help="fail instead of falling back to mock data")
    parser.add_argument("--offline", action="store_true",
                        help="build only from cached pages in data/raw (spends no API requests)")
    args = parser.parse_args()

    if args.offline:
        build_api_dataset(args.seasons, args.labels, offline=True)
        return

    if args.status:
        print(json.dumps(ApiFootballClient(config.API_KEY).status(), indent=2))
        return

    if args.mock or not config.API_KEY:
        if not args.mock:
            print("API_KEY not set in backend/.env - using mock dataset.")
        build_mock_dataset(args.labels)
        return

    try:
        build_api_dataset(args.seasons, args.labels)
    except (ApiFootballError, requests.RequestException) as exc:
        if args.no_fallback:
            raise
        print(f"API ingestion failed ({exc}). Falling back to mock dataset.")
        build_mock_dataset(args.labels)


if __name__ == "__main__":
    main()
