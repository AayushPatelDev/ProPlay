# ProPlay ⚽📈

Predict English Premier League player **market transfer values** from season stats.

- **Backend:** FastAPI · requests · pandas · scikit-learn · matplotlib/seaborn
- **Frontend:** React · Vite · Tailwind CSS v4 · Recharts
- **Model:** Linear Regression on log(market value), with a `ColumnTransformer` using `StandardScaler` for numbers and `OneHotEncoder` for position

```
ProPlay/
├── package.json              # root scripts: npm run dev → both servers (concurrently)
├── scripts/setup.sh          # one-shot install + data + train
├── backend/
│   ├── .env.example          # API_KEY="" and other settings → copy to .env
│   ├── requirements.txt
│   ├── app/
│   │   ├── config.py         # env loader + paths
│   │   ├── fetch_data.py     # API-Football ingestion (cached, rate-limited, resumable)
│   │   ├── features.py       # cleaning, cross-season aggregation, feature engineering
│   │   ├── labels.py         # market value labels: CSV merge or synthetic fallback
│   │   ├── mock_data.py      # offline dataset (fictional players, real clubs)
│   │   ├── train.py          # pipeline, metrics, plots, model.joblib
│   │   └── main.py           # FastAPI server (/api/*)
│   ├── data/
│   │   ├── raw/              # cached API pages (JSON)
│   │   ├── processed/        # player_seasons.csv + dataset_meta.json
│   │   └── market_values.example.csv
│   └── artifacts/            # model.joblib, metrics.json, predictions.csv, plots/*.png
└── frontend/
    ├── vite.config.js        # React + Tailwind plugins, /api + /plots proxy
    ├── index.html
    └── src/
        ├── index.css         # Tailwind @theme: the ProPlay palette
        ├── App.jsx
        ├── api/client.js
        ├── lib/              # formatting, debounce hook
        └── components/       # Header, PlayerSearch, PlayerCard, ValuationHero,
                              # WhatIfPanel, MetricsStrip, ValueScatter, DiagnosticsPlots
```

## Prerequisites

- Python 3.10+ (tested on 3.12)
- Node.js 20+ (tested on 23)

## Quick start

```bash
cd ~/Desktop/ProPlay
bash scripts/setup.sh     # venv, pip, dataset, training, npm install
npm run dev               # API on :8000 + UI on :5173
```

Open http://localhost:5173. The API docs are at http://127.0.0.1:8000/docs.

Without an API key, setup uses the **mock dataset**, so everything works offline right away.

## Step by step (manual)

### 1. Backend

```bash
cd ~/Desktop/ProPlay/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-train.txt   # API + data fetching + training
cp .env.example .env                    # then edit .env and set API_KEY
```

### 2. Get data

```bash
python -m app.fetch_data --status   # check your plan, allowed seasons, and remaining quota
python -m app.fetch_data            # API-Football if API_KEY is set, otherwise mock
python -m app.fetch_data --mock     # force offline mock data
python -m app.fetch_data --offline  # rebuild from cached API pages only (0 requests)
python -m app.fetch_data --seasons 2022 2023 --labels csv
```

The fetcher sends the `x-apisports-key` header. It calls `GET /teams?league=39&season=YYYY` once, then `GET /players?league=39&team=ID&season=YYYY&page=N` for each club. Going club by club is required because the free plan rejects `page` values above 3, which is far too few pages for a whole league. It:

- **Caches** every page in `data/raw/`, so a re-run never spends quota twice.
- **Rate-limits** requests (6.5 s apart by default) to stay under the free plan's 10 requests per minute.
- **Fetches newest seasons first.** One season costs about 61 requests (1 for the club list, plus about 3 pages per club). The free plan allows 100 requests a day, so that's roughly 1.5 seasons per day.
- **Resumes** after a failure. If you hit the daily cap, run the same command tomorrow and it continues where it stopped.
- A few clubs list more than 60 squad players (4 pages). Only the first 3 pages can be fetched, so some fringe or youth players are missing.
- Computes **age at the start of each season** from the birth date. The API's `age` field is the player's current age.
- Merges **mid-season transfers** into one row per player and season.
- **Removes duplicate stat lines.** Club-scoped queries also list a player's season under clubs they joined *later*, e.g. Rice's 2023/24 Arsenal season also appears under West Ham. These copies are inconsistent: same minutes (±5%) but different apps, missing goals, or 0-minute ghost rows. Without this step the stats would be summed and doubled. Genuine transfers split minutes between clubs, so they are kept. Which club label to keep is a heuristic (prefer goals reported, then fewer apps) and can occasionally pick the wrong club name. The stats themselves are correct.
- Falls back to mock data if the API fails. Pass `--no-fallback` to get an error instead.

> The free plan only covers some seasons (2022–2024 as of Sept 2026). If you get "Free plans do not have access to this season", set `SEASONS` in `.env` to the range the error message gives.

### 3. Train

```bash
python -m app.train
```

Training writes these files to `backend/artifacts/`:

| File | Contents |
|---|---|
| `model.joblib` | Final pipeline, fit on all rows |
| `metrics.json` | Hold-out R², R²(log), MAE, RMSE; 5-fold grouped CV; coefficients |
| `predictions.csv` | Out-of-fold predicted vs actual value for every row |
| `plots/actual_vs_predicted.png`, `residuals.png`, `coefficients.png` | Evaluation plots |

The train/test split and the cross-validation folds are **grouped by player**. The same player never appears in both training and evaluation, so seasons of one player can't leak into the test set.

### 4. Run

```bash
# terminal 1
cd ~/Desktop/ProPlay/backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# terminal 2
cd ~/Desktop/ProPlay/frontend
npm install
npm run dev
```

Or run both at once from the repo root: `npm install && npm run dev`.

After re-training, either restart the API or run `curl -X POST localhost:8000/api/reload`.

## Deploy to Vercel

The repo deploys as **one Vercel project** using [Services](https://vercel.com/docs/services), configured in `vercel.json`:

| Service | Root | What it is | Routes |
|---|---|---|---|
| `web` | `frontend/` | Vite build, served from the CDN | everything else |
| `api` | `backend/` | FastAPI (`app.main:app`) as a Python function | `/api/*`, `/plots/*` |

Steps:

1. Push to GitHub.
2. In Vercel, go to **Add New → Project**, import the repo, and keep the root directory as the repo root. Vercel reads `vercel.json`.
3. Deploy. No environment variables are needed. The API serves the committed model and data and never calls API-Football.

How it stays under Vercel's 500 MB Python function limit:

- `backend/requirements.txt` has only the runtime dependencies (FastAPI, pandas, numpy). Training tools (scikit-learn, matplotlib, etc.) live in `requirements-train.txt`.
- `train.py` exports the fitted pipeline to `artifacts/model.json`: scaler statistics, one-hot columns, coefficients and intercept. `predictor.py` serves predictions from that file with numpy. Training fails if the export doesn't reproduce scikit-learn's predictions exactly.
- The processed dataset, `model.json`, metrics, predictions and plots are committed. Raw API responses and `.env` are not.

To update the live model: fetch data and retrain locally, commit `backend/data/processed/` and `backend/artifacts/`, then push. Vercel redeploys automatically.

## Market value labels (important)

API-Football has **no market value endpoint on any plan**. It provides stats, not prices, so the target has to come from somewhere else. `LABEL_MODE` in `.env` controls where:

| Mode | Behaviour |
|---|---|
| `auto` (default) | Uses `data/market_values.csv` if the file exists, otherwise `synthetic` |
| `csv` | Real labels only. Players that can't be matched are dropped |
| `synthetic` | A fixed formula: position base × age curve × minutes × goals/assists × noise. **Demo only**, because the model learns this formula instead of the real market |

The dashboard shows a warning whenever labels are synthetic.

### Using real valuations (Transfermarkt via Kaggle)

1. Download the public **"Football Data from Transfermarkt"** dataset (`davidcariboo/player-scores`) from Kaggle.
2. Convert it to `backend/data/market_values.csv` with the columns `player_name,season,market_value_eur`:

```python
import pandas as pd
players = pd.read_csv("players.csv")[["player_id", "name"]]
vals = pd.read_csv("player_valuations.csv", parse_dates=["date"])
vals["season"] = vals["date"].dt.year.where(vals["date"].dt.month >= 7, vals["date"].dt.year - 1)
latest = vals.sort_values("date").groupby(["player_id", "season"]).tail(1)
out = latest.merge(players, on="player_id")[["name", "season", "market_value_in_eur"]]
out.columns = ["player_name", "season", "market_value_eur"]
out.to_csv("backend/data/market_values.csv", index=False)
```

(Adjust the column names if the dataset's schema has changed.)

3. Rebuild the data and retrain: `python -m app.fetch_data --labels csv && python -m app.train`

Names are matched without accents or case, and in several forms: full name, first name + last name, and the abbreviated `M. Salah` style that API-Football uses. The season is used when present. The log reports how many rows matched.

## API reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | `ok`, or `untrained` with instructions |
| GET | `/api/players?q=&limit=` | Accent-insensitive name search (latest season per player) |
| GET | `/api/players/{id}` | Stats, career totals, season history, label value |
| POST | `/api/predict` | Predicted value plus model metrics |
| GET | `/api/metrics` | Full `metrics.json` |
| GET | `/api/evaluation` | Out-of-fold actual vs predicted points |
| POST | `/api/reload` | Reload the model and data after re-training |
| GET | `/plots/{file}.png` | Evaluation plots |

`/api/predict` takes a `player_id`, any of the five stats, or both. Stats you pass override the player's real stats (this is how the what-if simulator works):

```bash
curl -X POST localhost:8000/api/predict -H 'content-type: application/json' \
  -d '{"goals": 20, "assists": 8, "minutes": 3100, "age": 24, "position": "Attacker"}'
```

```json
{
  "predicted_value_eur": 102380000.0,
  "actual_value_eur": null,
  "currency": "EUR",
  "label_source": "synthetic",
  "metrics": { "test": { "r2": 0.533, "r2_log": 0.608, "mae": 3984886, "rmse": 6030893 }, "cv": { "...": "..." } }
}
```

## Model notes

- **Inputs:** goals, assists, minutes, age, position
- **Engineered features:** `age_sq = (age − 26)²`, which lets a linear model capture a mid-career value peak, and `ga_per90` (goals + assists per 90 minutes)
- **Target transform:** the model is fit on `log1p(value)` and predictions are converted back with `expm1`. Transfer values are heavily skewed, and fitting in log space avoids negative predictions
- **R² vs R²(log):** R² in euros is dominated by a few very expensive players, so both are reported
- Coefficients are shown as the % change in predicted value per +1 standard deviation. Positions are relative to Goalkeeper

## Design system

Adapted from the **Wise** DESIGN.md in [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md). One lime accent sits on a sage canvas with near-black ink and white cards. Elevation comes from surface contrast rather than shadows. Cards and buttons use a 24px radius, and headline numbers use weight 900.

Tokens live in `frontend/src/index.css` (`@theme`). Reusable component classes are defined there too.

| Token | Hex | Role |
|---|---|---|
| `primary` | `#9fe870` | Brand accent, primary CTA, valuation number |
| `ink` | `#0e0f0c` | Text, dark hero card, selected chips, footer |
| `body` / `mute` | `#454745` / `#868685` | Secondary text / fine print |
| `canvas` | `#ffffff` | Cards |
| `canvas-soft` | `#e8ebe6` | Page background, stat tiles, secondary buttons |
| `positive` / `negative` / `warning` | `#2ead4b` / `#d03238` / `#ffd11a` | Status only. Lime is never used as "success" |

| Class | Use |
|---|---|
| `.card` / `.card-sage` / `.card-dark` | White, sage, and ink surfaces (24px radius, 24px padding) |
| `.btn` + `.btn-primary` / `.btn-secondary` / `.btn-tertiary` (+ `.btn-sm`) | Lime CTA, sage secondary, ink-outline tertiary |
| `.chip` + `.chip-on` / `.chip-off` | Filters, tabs, segmented controls (selected = ink with lime text) |
| `.badge-*` | Status pills |
| `.input`, `.range` | 1px ink-border input; ink-filled slider with lime thumb |

## Troubleshooting

- **UI says "Can't reach the model":** the API isn't running, or the model isn't trained. Run `python -m app.train`, then start uvicorn.
- **`{"errors": {"token": ...}}`:** the key in `backend/.env` is wrong. It must be an API-Sports dashboard key. For a RapidAPI key, set `API_BASE_URL` accordingly and change the header in `fetch_data.py` to `x-rapidapi-key`.
- **Daily limit reached:** cached pages are kept. Re-run `fetch_data` tomorrow.
- **Port in use:** change `--port` in the root `package.json` and the proxy target in `vite.config.js`.
