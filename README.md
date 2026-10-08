# AI-Based Agricultural Marketplace  (v2)
Farmer–buyer matching and net realization optimization, implementing the patent drawings in `docs/patent_drawings/`.

```
agri-marketplace/
├── backend/        FastAPI + SQLAlchemy + Alembic + APScheduler (API, offers, alerts, admin, jobs, WebSocket)
├── ml/             multi-horizon price models, conformal intervals, drift check, data importers, experiments
├── frontend/       React PWA: English/Telugu, voice input, offline cache, farmer / buyer / admin apps
├── docs/           patent mapping, feature map, assumptions, roadmap status, experiment guide
├── .github/        CI (tests + migrations + frontend build)
└── docker-compose.yml
```

## What's new in v2
| Area | Features |
|---|---|
| Forecasting | 3/7/14-day price models, **80% prediction intervals** (conformal), **sell-now-vs-wait** advice, drift check + scheduled retraining |
| Marketplace | **Offers & counter-offers**, payment tracking (UPI/bank/cash reference), **disputes**, **ratings** (feed buyer reliability), decision-feedback records |
| Farmers | **Farmer groups** (pooled lots), **MSP warnings**, truck capacity / multiple trips, price **alerts** (in-app, SMS/WhatsApp via Twilio) |
| Real data | Agmarknet daily fetch, **CSV importer**, Open-Meteo rainfall, arrivals merge, one `build_dataset` command |
| Distance | Optional **OSRM** road distance (cached, falls back automatically) |
| UX | **Telugu UI**, **voice input**, installable **PWA** with offline cache, live updates over **WebSocket** |
| Admin | Dashboard: data-quality alerts, disputes, markets, model metrics, job triggers, audit log |
| Engineering | Alembic migrations, rate limiting, audit log, configurable CORS, CI, 27 backend + 4 ML + 7 frontend tests |
| Report | **Headline experiment**, **ablation study**, weight tuning, demand-index validation, baseline benchmarks |

See `docs/roadmap_status.md` for exactly what is done, partial, or not done.

## Run it (Windows PowerShell shown; Mac/Linux use `source .venv/bin/activate`)
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt

# 1) models (synthetic data is generated automatically; 3 horizons + demand model take ~10-30 minutes on a laptop)
python -m ml.train_price
python -m ml.train_demand

# 2) backend  -> http://localhost:8000/docs
cd backend
python -m app.seed
uvicorn app.main:app --reload

# 3) frontend (new terminal) -> http://localhost:5173
cd frontend
npm install
npm run dev
```
Demo logins: farmer `8000000001 / farmer123` (Telugu notifications), buyer `9000000001 / buyer123`, admin `9999999999 / admin123`.
Quick start without waiting for training: `python -m ml.train_price --horizons 7` (the app falls back to a statistical estimate for horizons that are missing).

## Docker
```bash
docker compose up --build       # Postgres + migrations + seed + API :8000 + frontend :5173
docker compose exec backend python -m ml.train_price
docker compose exec backend python -m ml.train_demand
```

## Tests
```bash
cd backend && python -m pytest -q          # backend (27)
python -m pytest ml/tests -q               # ML utilities (4), run from repo root
cd frontend && npm test                    # frontend (7)
```

## Real data (do this before quoting any accuracy number)
```bash
export DATA_GOV_API_KEY=<key from data.gov.in>                    # PowerShell: $env:DATA_GOV_API_KEY="..."
python -m ml.data_ingestion.fetch_agmarknet                       # latest day only -> run daily (the scheduler does it when the key is set)
python -m ml.data_ingestion.import_csv path/to/agmarknet_export.csv   # bulk history exported from the Agmarknet site
python -m ml.data_ingestion.fetch_weather --start 2024-01-01 --end 2026-10-01
python -m ml.data_ingestion.build_dataset                         # merge + clean -> ml/data/market_prices.csv
python -m ml.train_price && python -m ml.train_demand
```

## Experiments for the report
```bash
python -m ml.experiments.headline --samples 1500     # system vs nearest mandi, with 95% CIs
python -m ml.experiments.ablation --samples 1500
python -m ml.experiments.validate_demand
python -m ml.experiments.benchmarks
python -m ml.experiments.tune_weights
```
Results are written to `ml/experiments/results/`. With the bundled **synthetic** data they only demonstrate the pipeline; rerun on real data for reportable numbers.

## Configuration
Copy `.env.example` to `.env` in the repo root (backend settings are loaded automatically). For the frontend API address create `frontend/.env.local` with `VITE_API_URL=http://localhost:8000`.

All assumptions and switches are environment variables with defaults in `backend/app/config.py` (see `.env.example` and `docs/assumptions.md`).
Production checklist: set `SECRET_KEY`, `CORS_ORIGINS`, `AUTO_CREATE_TABLES=0` + `alembic upgrade head`, use PostgreSQL, serve behind HTTPS, run a single scheduler instance (or move jobs to a worker), self-host OSRM.
