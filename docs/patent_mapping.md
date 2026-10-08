# Patent figure -> code mapping

| Ref | Patent element | Implementation |
|---|---|---|
| 110 / 111 | Farmer / buyer client apps | `frontend/src/farmer/`, `frontend/src/buyer/` |
| 120 | Secure API channel | `backend/app/security.py` (JWT), HTTPS at deployment, `backend/app/api/` |
| 130 | Backend server | `backend/app/main.py`, `backend/app/services/recommender.py` |
| 140 | Crop, buyer & market DB | `backend/app/models/models.py` (users, listings, requirements, markets) |
| 142 | Historical/current market data | `MarketPrice` table, `ml/data_ingestion/` |
| 150 | AI market intelligence engine | `ml/predict.py`, `backend/app/services/price_service.py` |
| 160 | Cloud hosting | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` |
| 210 / 215 | Farmer / buyer input | `POST /farmer/listings`, `POST /buyer/requirements` |
| 220 | Store with market data | SQLAlchemy models |
| 230 / 520 | Price & demand prediction (ML ensemble) | `ml/ensemble.py`, `ml/train_price.py`, `ml/train_demand.py` |
| 240 / 530 | Buyer-market matching | `backend/app/services/matching.py` |
| 250 / 540 | Transport cost & net realization | `services/transport.py`, `services/net_realization.py` |
| 260 / 540 | Risk analysis & ranking | `services/risk.py`, `services/ranking.py` |
| 270 / 550 | Explainable recommendation | `GET /recommendations/{id}/explain`, `ml/explain.py` (SHAP) |
| 510 | Normalization / feature extraction | `ml/features.py` |
| 300-350 | Crop Selling Opportunity Record | `Opportunity` model (timestamp, risk tag, crop details, match details, model output) |
| 410-450 | Farmer dashboard cards | `frontend/src/farmer/FarmerDashboard.jsx` |
