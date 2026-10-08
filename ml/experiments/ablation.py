"""ABLATION STUDY: what happens when a component is removed?  python -m ml.experiments.ablation --samples 1500"""
import argparse
from pathlib import Path

import numpy as np

from .backtest import Strategy, bootstrap_ci, prepare, simulate

OUT = Path(__file__).parent / "results"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=1500)
    a = ap.parse_args()
    table, cutoff = prepare()
    strategies = [Strategy("full_system"),
                  Strategy("no_forecast (today's price)", use_forecast=False),
                  Strategy("no_transport_cost", use_transport=False),
                  Strategy("no_risk_term", use_risk=False),
                  Strategy("no_demand_signal", use_demand=False),
                  Strategy("nearest_mandi", nearest_only=True)]
    res = simulate(table, strategies, a.samples)
    full = res["full_system"].values
    lines = [f"# Ablation study ({a.samples} simulated sales after {cutoff.date()})\n",
             "| Variant | Mean realized net Rs/q | vs full system | 95% CI of difference |", "|---|---|---|---|"]
    for s in strategies:
        v = res[s.name].values
        d = v - full
        lo, hi = bootstrap_ci(d)
        lines.append(f"| {s.name} | {v.mean():.0f} | {d.mean():+.1f} | [{lo:+.1f}, {hi:+.1f}] |")
    OUT.mkdir(exist_ok=True)
    (OUT / "ablation.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
