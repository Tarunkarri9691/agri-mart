import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_agri.db"
os.environ["ENABLE_SCHEDULER"] = "0"
os.environ["RATE_LIMIT_PER_MIN"] = "0"
os.environ["AUTH_RATE_LIMIT_PER_MIN"] = "0"
os.environ["USE_OSRM"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
