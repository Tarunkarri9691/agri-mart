# Headline experiment (800 simulated sales after 2025-11-12, 7-day horizon)

Realized net per quintal uses the ACTUAL later price and the true transport cost. Gain is the system pick vs each baseline.

| Baseline | Baseline net Rs/q | System net Rs/q | Mean gain Rs/q | Mean gain % | 95% CI of gain % | System better in |
|---|---|---|---|---|---|---|
| nearest_mandi | 6029 | 6319 | 290 | 4.61% | [4.17%, 5.04%] | 63% of cases |
| highest_current_price | 6318 | 6319 | 0 | 0.64% | [0.40%, 0.90%] | 26% of cases |

Oracle (best mandi in hindsight) net: 6407 Rs/q; the system captures 98.7% of it.