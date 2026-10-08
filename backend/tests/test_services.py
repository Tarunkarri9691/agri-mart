from datetime import date

import pytest

from app.services import matching
from app.services.net_realization import compute_net_realization, spoilage_loss_rate
from app.services.ranking import rank_candidates
from app.services.risk import risk_assessment, risk_tag
from app.services.transport import haversine_km, road_distance_km, transport_cost


def test_haversine_eluru_vijayawada():
    assert 45 < haversine_km(16.7107, 81.0952, 16.5062, 80.6480) < 60


def test_road_distance_is_longer_than_straight_line():
    assert road_distance_km(16.7107, 81.0952, 16.5062, 80.6480) > haversine_km(16.7107, 81.0952, 16.5062, 80.6480)


def test_transport_cost_formula_and_minimum():
    # 100 q * 100 km * 0.6 + 100 * 15 = 7500
    assert transport_cost(100, 100) == 7500
    assert transport_cost(1, 1) == 1500  # minimum trip charge


def test_net_realization_breakdown():
    r = compute_net_realization(2000, 100, 5000, 0.02, 0.01)
    assert r["gross_value"] == 200000
    assert r["commission"] == 4000 and r["expected_loss"] == 2000
    assert r["net_realization"] == 189000


def test_banana_spoils_faster_than_paddy():
    assert spoilage_loss_rate("banana", 10) > spoilage_loss_rate("paddy", 10)


def test_risk_tag_thresholds():
    assert risk_tag(0.1) == "low" and risk_tag(0.4) == "moderate" and risk_tag(0.8) == "high"


def test_risk_increases_with_distance_and_unreliability():
    near = risk_assessment(0.05, 0.6, 20, 4.8, 0.001)
    far = risk_assessment(0.05, 0.6, 350, 2.0, 0.001)
    assert far["score"] > near["score"]


def test_matching_gates_and_scores():
    d = date(2026, 10, 1), date(2026, 10, 30)
    ok = matching.compatibility("paddy", 100, "B", *d, "paddy", 100, "B", *d)
    assert ok == 1.0
    assert matching.compatibility("paddy", 100, "B", *d, "maize", 100, "B", *d) == 0.0  # crop must match
    assert matching.compatibility("paddy", 100, "B", *d, "paddy", 100, "B",
                                  date(2026, 12, 1), date(2026, 12, 5)) == 0.0          # no date overlap
    assert matching.compatibility("paddy", 50, "C", *d, "paddy", 100, "A", *d) < ok       # weaker match


def test_ranking_prefers_high_net_low_risk():
    items = [
        {"net_realization": 100000, "compatibility": 0.9, "risk_score": 0.7},
        {"net_realization": 95000, "compatibility": 0.9, "risk_score": 0.1},
    ]
    ranked = rank_candidates(items, 100)
    assert ranked[0]["risk_score"] == 0.1 and ranked[0]["rank"] == 1


def test_ranking_empty():
    assert rank_candidates([], 100) == []
