# Status of every suggested improvement (honest)

Legend: ✅ built and tested here · 🟡 built, but needs your keys/data/accounts or could not be tested in my sandbox · ❌ not built

## 1. Make the results real
| Item | Status | Notes |
|---|---|---|
| Real Agmarknet data | 🟡 | `fetch_agmarknet`, `import_csv` (tested with a fake export), `build_dataset` (tested). Needs your data.gov.in key; I could not call the live API. Fetch returns the latest day only, so history comes from the CSV importer + daily job. |
| Real arrivals and weather | 🟡 | `fetch_weather` (Open-Meteo, free) and arrivals-file merge. Merge is tested; the live weather call was not (sandbox has no internet). |
| Validate the demand index | ✅ | `ml/experiments/validate_demand.py` |
| Calibrate cost assumptions | ❌ | Needs your field survey of truck operators/traders. Edit `backend/app/config.py`. |

## 2. Better ML
| Item | Status | Notes |
|---|---|---|
| Forecast ranges | ✅ | Split-conformal 80% intervals per crop; coverage is reported at training. Intervals feed the risk score and the net-realization range. |
| Prophet / LSTM | ❌ | Not installed/trained (heavy dependencies). `benchmarks.py` compares against naive, seasonal-naive and Holt-Winters; add Prophet there if you want it. |
| Multi-horizon + sell-now-vs-wait | ✅ | 3/7/14-day models; `GET /recommendations/{id}/timing` |
| Learn from outcomes | 🟡 | Deals record rank/price gap; ratings update buyer reliability (Bayesian average). Ranking weights are NOT auto-tuned from live data (too little data); `tune_weights.py` tunes them on a backtest instead. |
| Scheduled retraining + drift | ✅ | Daily drift check, weekly retrain, `POST /admin/retrain`. Scheduler wiring is tested only by calling the job functions, not by waiting for cron. |

## 3. Features farmers use
| Item | Status | Notes |
|---|---|---|
| Telugu UI + voice | 🟡 | ~70 Telugu strings (please have a native speaker review) and speech parsing (unit-tested). The microphone itself depends on browser support (Chrome/Edge) and was not tested here. |
| SMS / WhatsApp alerts | 🟡 | In-app + WebSocket tested. Twilio sending is coded but untested (needs your account; WhatsApp needs an approved sender). Default `console` provider just logs. |
| Real road distance, truck capacity | 🟡 | Truck trips are tested. OSRM code path has a safe fallback but the live call was not tested. |
| Farmer groups | ✅ | Pooled lot, pooling gain, member shares (quantity-proportional) |
| Offers and acceptance | ✅ | Offer, counter, accept, reject, cancel, payment, confirm |
| Offline PWA | 🟡 | Manifest + service worker built; build verified, offline behavior not tested in a browser. |

## 4. Trust and operations
| Item | Status | Notes |
|---|---|---|
| Buyer ratings | ✅ | |
| Payment tracking | 🟡 | Records UPI/bank/cash references and a two-sided confirmation. It does **not** move money or integrate a payment gateway. |
| Dispute flow | ✅ | Open, admin resolves (deal stands / cancel) |
| Admin dashboard | ✅ | |
| MSP comparison | 🟡 | Flags prices below MSP. MSP values in `backend/app/data/msp.json` are from memory (2025-26) for paddy, maize, cotton: **verify against the official notification.** |

## 5. Engineering
| Item | Status | Notes |
|---|---|---|
| Alembic migrations | ✅ | Initial migration generated and applied on SQLite; verify once on PostgreSQL |
| Background jobs | ✅ | APScheduler in-process (single instance). Celery not used. |
| WebSocket live updates | ✅ | Tested end to end |
| Rate limiting, audit log, CORS | ✅ | In-memory limiter (one process). Use Redis for multi-worker. |
| CI | 🟡 | Workflow file included; not run on GitHub from here |
| Frontend tests | 🟡 | 7 unit tests for pure logic (i18n, formatting, voice parsing). No component/browser tests. |
| PostGIS | 🟡 | Replaced by a bounding-box + radius pre-filter, which is enough at this scale. PostGIS not used. |

## 6. Report and patent
| Item | Status |
|---|---|
| Headline experiment, ablation, weight tuning | ✅ code; numbers in `ml/experiments/results/` are from **synthetic** data |
| Pilot with real farmers | ❌ (needs you) |
| Patent feature map | ✅ `docs/feature_map.md` |
