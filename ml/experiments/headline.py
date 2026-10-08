"""HEADLINE EXPERIMENT: net realization of the system's top pick vs the nearest mandi (what most farmers do),
vs the mandi with the highest current price, with 95% bootstrap confidence intervals.
    python -m ml.experiments.headline --samples 1500
Writes ml/experiments/results/headline.md and .csv"""
import argparse
from pathlib import Path

import numpy as np

from .backtest import Strategy, bootstrap_ci, prepare, simulate

OUT = Path(__file__).parent / "results"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=1500)
    ap.add_argument("--horizon", type=int, default=7)
    a = ap.parse_args()
    table, cutoff = prepare(a.horizon)
    strategies = [Strategy("system_top_pick"), Strategy("nearest_mandi", nearest_only=True),
                  Strategy("highest_current_price", highest_current_price=True)]
    res = simulate(table, strategies, a.samples, horizon=a.horizon)
    OUT.mkdir(exist_ok=True)
    res.to_csv(OUT / "headline.csv", index=False)

    lines = [f"# Headline experiment ({a.samples} simulated sales after {cutoff.date()}, {a.horizon}-day horizon)\n",
             "Realized net per quintal uses the ACTUAL later price and the true transport cost. Gain is the system pick vs each baseline.\n",
             "| Baseline | Baseline net Rs/q | System net Rs/q | Mean gain Rs/q | Mean gain % | 95% CI of gain % | System better in |",
             "|---|---|---|---|---|---|---|"]
    sysnet = res["system_top_pick"].values
    for b in ("nearest_mandi", "highest_current_price"):
        base = res[b].values
        gain_pct = (sysnet - base) / np.abs(base) * 100
        lo, hi = bootstrap_ci(gain_pct)
        lines.append(f"| {b} | {base.mean():.0f} | {sysnet.mean():.0f} | {(sysnet - base).mean():.0f} | {gain_pct.mean():.2f}% | "
                     f"[{lo:.2f}%, {hi:.2f}%] | {np.mean(sysnet > base):.0%} of cases |")
    regret = (res["oracle"] - sysnet) / res["oracle"] * 100
    lines.append(f"\nOracle (best mandi in hindsight) net: {res['oracle'].mean():.0f} Rs/q; the system captures "
                 f"{100 - regret.mean():.1f}% of it.")
    (OUT / "headline.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
