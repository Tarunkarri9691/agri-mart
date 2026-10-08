"""Central configuration. All business assumptions live here so results are reproducible
(report these in the assumptions table of your project report)."""
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(os.getenv("REPO_ROOT", Path(__file__).resolve().parents[2]))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))  # makes the `ml` package importable

try:  # optional: load settings from <repo>/.env (copy .env.example to .env)
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agri.db")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# ---- Transport assumptions (Rs, quantities in quintals = 100 kg) ----
RATE_PER_QUINTAL_KM = float(os.getenv("RATE_PER_QUINTAL_KM", "0.6"))
LOADING_COST_PER_QUINTAL = float(os.getenv("LOADING_COST_PER_QUINTAL", "15"))
MIN_TRIP_CHARGE = float(os.getenv("MIN_TRIP_CHARGE", "1500"))
ROAD_FACTOR = 1.3          # road distance ~= straight line * factor (fallback to OSRM/Google)
AVG_SPEED_KMPH = 40.0

# ---- Commission ----
MARKET_COMMISSION_PCT = 0.02   # mandi commission / market fee
DIRECT_COMMISSION_PCT = 0.005  # platform fee on direct buyer sale

# ---- Spoilage: fraction of value lost per day in transit ----
SPOILAGE_PER_DAY = {"paddy": 0.002, "maize": 0.003, "cotton": 0.001, "chilli": 0.01, "banana": 0.06}
DEFAULT_SPOILAGE_PER_DAY = 0.01

# ---- Risk ----
RISK_WEIGHTS = {
    "price_volatility": 0.25,
    "demand_uncertainty": 0.20,
    "distance": 0.15,
    "buyer_reliability": 0.20,
    "spoilage": 0.20,
}
RISK_LOW_MAX = 0.30
RISK_MODERATE_MAX = 0.50

# ---- Ranking: Score = W_NET*NetRealization(norm) + W_COMPAT*Compatibility - W_RISK*Risk ----
RANK_W_NET = float(os.getenv("RANK_W_NET", "0.5"))
RANK_W_COMPAT = float(os.getenv("RANK_W_COMPAT", "0.3"))
RANK_W_RISK = float(os.getenv("RANK_W_RISK", "0.2"))

MIN_COMPATIBILITY = 0.3
PREDICTION_HORIZON_DAYS = 7

# ================= v2 additions =================
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
AUTO_CREATE_TABLES = os.getenv("AUTO_CREATE_TABLES", "1") == "1"   # use Alembic migrations in production (set 0)

# ---- Routing (OSRM) ----
USE_OSRM = os.getenv("USE_OSRM", "0") == "1"       # public demo server is rate-limited; self-host OSRM for real use
OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org")
TRUCK_CAPACITY_QUINTALS = float(os.getenv("TRUCK_CAPACITY_QUINTALS", "100"))  # one truck load (10 tonnes)
MAX_MATCH_RADIUS_KM = float(os.getenv("MAX_MATCH_RADIUS_KM", "350"))

# ---- Forecast horizons / waiting ----
HORIZONS = (3, 7, 14)
STORAGE_COST_PER_QUINTAL_DAY = float(os.getenv("STORAGE_COST_PER_QUINTAL_DAY", "1.0"))
STORAGE_LOSS_PER_DAY = {"paddy": 0.0005, "maize": 0.0005, "cotton": 0.0003, "chilli": 0.001, "banana": 0.05}
DEFAULT_STORAGE_LOSS_PER_DAY = 0.002
WAIT_MIN_GAIN_PCT = 3.0        # wait only if expected net improves by at least this much
WAIT_MAX_DOWNSIDE_PCT = 10.0   # ...and the pessimistic (10th percentile) case is at most this much worse than selling now

# ---- MSP ----
_msp_path = Path(__file__).parent / "data" / "msp.json"
MSP = {k: v for k, v in json.loads(_msp_path.read_text()).items() if not k.startswith("_")} if _msp_path.exists() else {}

# ---- Ratings (Bayesian average pulls new users toward the prior) ----
RATING_PRIOR = 4.0
RATING_PRIOR_WEIGHT = 3

# ---- Security / ops ----
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "120"))
AUTH_RATE_LIMIT_PER_MIN = int(os.getenv("AUTH_RATE_LIMIT_PER_MIN", "20"))
AUDIT_LOG = os.getenv("AUDIT_LOG", "1") == "1"
ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "1") == "1"
RECOMPUTE_CHANGE_PCT = 5.0     # notify farmer when best net realization moves by this much

# ---- Notifications: console (default) | twilio_sms | twilio_whatsapp ----
NOTIFY_PROVIDER = os.getenv("NOTIFY_PROVIDER", "console")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_FROM", "")             # e.g. +1415... or whatsapp:+14155238886
DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY", "")
