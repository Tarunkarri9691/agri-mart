"""Grid-search ranking weights (net, compatibility, risk) that maximize realized net on a TRAINING part of the backtest,
then report them on a held-out part so the improvement is not overfit.   python -m ml.experiments.tune_weights"""
import itertools
import argparse

from .backtest import Strategy, prepare, simulate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=800)
    a = ap.parse_args()
    table, _ = prepare()
    grid = [(wn, wr) for wn, wr in itertools.product([0.3, 0.5, 0.7, 0.9], [0.0, 0.1, 0.2, 0.4])]
    strategies = [Strategy(f"n{wn}_r{wr}", w_net=wn, w_compat=0.3, w_risk=wr) for wn, wr in grid]
    fit = simulate(table, strategies, a.samples, seed=1)
    best = max(strategies, key=lambda s: fit[s.name].mean())
    held = simulate(table, [best, Strategy("default")], a.samples, seed=2)
    print(f"Best weights on tuning cases: net={best.w_net} risk={best.w_risk}")
    print(f"Held-out realized net Rs/q: tuned={held[best.name].mean():.1f}  default={held['default'].mean():.1f}")
    print("Only adopt tuned weights if the held-out gain is clearly positive; otherwise keep the defaults in config.py.")


if __name__ == "__main__":
    main()
