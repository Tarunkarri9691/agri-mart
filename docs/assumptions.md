# Assumptions table (cite in the report so results are reproducible)
All values live in `backend/app/config.py` and can be overridden with environment variables.

| Parameter | Default | Notes |
|---|---|---|
| Transport rate | ₹0.60 per quintal-km | = ₹6 per tonne-km; adjust to local truck rates |
| Loading/unloading | ₹15 per quintal | |
| Minimum trip charge | ₹1,500 | |
| Road distance factor | 1.3 × straight-line | Replace with OSRM/Google distance |
| Average speed | 40 km/h | Used for travel time and spoilage |
| Mandi commission | 2% | |
| Direct-sale platform fee | 0.5% | |
| Spoilage per day | paddy 0.2%, maize 0.3%, cotton 0.1%, chilli 1%, banana 6% | Share of value lost per transit day |
| Risk weights | volatility .25, demand .20, distance .15, buyer reliability .20, spoilage .20 | Score 0-1 |
| Risk tags | low < 0.30 ≤ moderate < 0.50 ≤ high | |
| Ranking weights | net .5, compatibility .3, risk .2 | `Score = .5·Net(norm) + .3·Compat − .2·Risk` |
| Net normalization | ratio to best option | |
| Prediction horizon | 7 days | Model predicts the 7-day price change |

Formulas
- Transport = max(rate × km × quintals + loading × quintals, minimum charge)
- Net realization = price × qty − transport − commission − expected spoilage loss
- Compatibility = 0.4·quantity coverage + 0.3·quality match + 0.3·date overlap (crop must match, dates must overlap)
- Demand index = clip(0.5 + 2.5·(price momentum − 1) − (arrival ratio − 1), 0, 1)

## v2 assumptions
| Parameter | Default | Notes |
|---|---|---|
| Truck capacity | 100 quintals (10 t) | A 250-quintal lot needs 3 trips; the minimum charge applies per trip |
| Match radius | 350 km | Buyers/markets farther away are ignored |
| Storage cost | ₹1 per quintal per day | Used by sell-now-vs-wait |
| Storage loss per day | paddy/maize 0.05%, cotton 0.03%, chilli 0.1%, banana 5% | |
| Wait rule | expected gain ≥ 3% and pessimistic case ≤ 10% worse than selling now | |
| Prediction interval | 80% conformal, per crop | Calibrated on the most recent 15% of training data |
| Risk input for mandis | 0.5 × recent price swing + interval half-width | Buyers with fixed offers use recent swing only |
| Rating prior | 4.0 with weight 3 | New users start near 4.0 |
| Alert / re-rank notify threshold | best net moves by 5% | |
| MSP | `backend/app/data/msp.json` | Verify against the official notification |
| Rate limit | 120 requests/min per IP (20 for /auth) | In memory |
