# Experiments guide

All experiments live in `ml/experiments/` and reuse the production transport, net-realization, risk and ranking code.

| Script | Question it answers | Output |
|---|---|---|
| `headline.py` | How much more net money does the system's top pick realize than the nearest mandi / the highest current price? | `results/headline.md` (mean gain, 95% bootstrap CI, win rate, share of the oracle captured) |
| `ablation.py` | What does each component add (forecast, transport cost, risk, demand)? | `results/ablation.md` |
| `tune_weights.py` | Better ranking weights? (tuned on one set of cases, checked on another) | console |
| `validate_demand.py` | Does the demand index predict later price rises? | console |
| `benchmarks.py` | Ensemble vs naive / seasonal-naive / Holt-Winters | console |

## Method (no look-ahead)
1. Train the price model only on data before a cutoff date (outcome windows also end before it).
2. Simulate random sales after the cutoff: random date, crop, farm location near a market, quantity.
3. Each strategy chooses a mandi using only information available on that date.
4. Realized net uses the **actual** price `horizon` days later and the true transport cost.

## Limits to state in your report
- Only mandis are simulated; there is no real history of direct-buyer offers.
- With the bundled synthetic data the results show the pipeline works, not real-world gains. Rebuild the dataset from Agmarknet and rerun.
- The simulated sale happens exactly `horizon` days after the decision; real farmers sell when they choose.

## Results on the BUNDLED SYNTHETIC data (800 simulated sales, 7-day horizon)
These come from generated data, so they show the pipeline works. They are **not** evidence about real markets.

| Check | Result |
|---|---|
| System top pick vs nearest mandi | +4.6% net per quintal, 95% CI [4.2%, 5.0%], better in 63% of cases |
| System vs mandi with highest current price | +0.6% (CI [0.4%, 0.9%]), better in 26% of cases (ties/near-ties are common) |
| Share of the hindsight-best mandi's net captured | 98.7% |
| Price model MAPE (7-day), ensemble vs "last price" | 2.05% vs 2.27% (3-day: 1.39% vs 1.45%; 14-day: 2.76% vs 3.42%) |
| 80% interval empirical coverage | 78.9% (3-day), 78.3% (7-day), 76.7% (14-day): slightly under the 80% target |
| Holt-Winters / seasonal naive (MAPE) | 2.37% / 7.01% |
| Demand index vs next-week price change | Spearman rho -0.009: no signal on synthetic data |
| Weight tuning (held-out) | tuned 6474 vs default 6477 Rs/q: keep defaults |

### What the ablation shows, and why you should not over-read it
- Removing the forecast, transport cost or demand term changes realized net by less than the confidence interval (about ±0.1%) or slightly in favor of removal. In synthetic data, price differences between markets are a fixed random offset, so *choosing the right market* matters far more than any of these refinements.
- Removing the risk term raises mean realized net by about ₹25 per quintal (0.4%). That is expected: the risk term deliberately trades a little expected income for lower risk. If your report claims risk-adjusted benefit, measure a risk-adjusted metric (for example worst-decile net) instead of the mean.
- On real data these components may behave differently. Rerun `ablation.py` after `build_dataset` and report what you actually find, including components that do not help.
