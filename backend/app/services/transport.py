"""Distance + transportation cost (patent step 250). Real road distance via OSRM when enabled, else Haversine x factor."""
import logging
import math
import time

from .. import config

log = logging.getLogger(__name__)
_route_cache: dict = {}
_osrm_down_until = 0.0


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _osrm_km(lat1, lon1, lat2, lon2):
    """Road distance from an OSRM server. Cached; backs off for 5 min if the server is unreachable."""
    global _osrm_down_until
    key = (round(lat1, 3), round(lon1, 3), round(lat2, 3), round(lon2, 3))
    if key in _route_cache:
        return _route_cache[key]
    if time.time() < _osrm_down_until:
        return None
    try:
        import httpx
        r = httpx.get(f"{config.OSRM_URL}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}",
                      params={"overview": "false"}, timeout=2.5)
        km = r.json()["routes"][0]["distance"] / 1000.0
        _route_cache[key] = km
        return km
    except Exception as exc:
        log.warning("OSRM unavailable (%s); using straight-line estimate for 5 minutes", exc)
        _osrm_down_until = time.time() + 300
        return None


def road_distance_km(lat1, lon1, lat2, lon2) -> float:
    if config.USE_OSRM:
        km = _osrm_km(lat1, lon1, lat2, lon2)
        if km is not None:
            return round(km, 1)
    return round(haversine_km(lat1, lon1, lat2, lon2) * config.ROAD_FACTOR, 1)


def travel_hours(distance_km: float) -> float:
    return distance_km / config.AVG_SPEED_KMPH


def trips_needed(quantity_quintals: float) -> int:
    return max(1, math.ceil(quantity_quintals / config.TRUCK_CAPACITY_QUINTALS))


def transport_cost(distance_km: float, quantity_quintals: float) -> float:
    """rate x distance x quantity + loading, never below the minimum charge for each truck trip."""
    variable = config.RATE_PER_QUINTAL_KM * distance_km * quantity_quintals
    loading = config.LOADING_COST_PER_QUINTAL * quantity_quintals
    return round(max(variable + loading, trips_needed(quantity_quintals) * config.MIN_TRIP_CHARGE), 2)
