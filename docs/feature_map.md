# Feature map: new capabilities vs the patent drawings

| New capability | Patent element it extends | Code |
|---|---|---|
| Multi-horizon forecast + prediction interval | 150 / 520 price & demand prediction (ML ensemble) | `ml/train_price.py`, `ml/conformal.py`, `ml/predict.py` |
| Sell-now vs wait advice | 260 risk analysis & ranking; 270/550 recommendation | `backend/app/services/timing.py` |
| Forecast uncertainty in risk score; net-realization range | 260 / 540 risk ranking; FIG. 3 ref 350 | `services/recommender.py`, `services/risk.py` |
| Truck trips, real road distance | 250 / 540 transportation cost & distance | `services/transport.py` |
| MSP check | 350 / 450 recommendation content | `services/recommender.py`, `data/msp.json` |
| Offers, counter-offers, payment, disputes | 240 matching -> transaction (extension) | `api/offers.py` |
| Ratings -> buyer reliability -> risk | 260 risk (buyer reliability factor) | `api/offers.py`, `services/risk.py` |
| Decision feedback (Outcome records) | FIG. 3 record 300 (history of opportunities) | `models/Outcome`, `api/offers.py` |
| Farmer groups / pooled lots | 240 matching by quantity | `api/groups.py` |
| Scheduled re-ranking, live push | "recommendations can be updated when new data becomes available" (abstract) | `jobs.py`, `ws.py` |
| Price & best-option alerts | abstract: update on new market data | `jobs.py`, `services/notifier.py` |
| Drift check, retraining | 150 engine maintenance | `ml/drift.py`, `jobs.py` |
| Telugu UI, voice, PWA | 110 farmer client application | `frontend/src/` |
| Admin dashboard, audit log | 130 backend server (operations) | `api/admin.py`, `middleware.py` |

Note for the patent attorney: items marked "extension" go beyond the drawings; consider whether additional drawings/claims are needed.
