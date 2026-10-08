"""Split-conformal prediction intervals on the predicted 7-day return.
Residuals are computed on a held-out calibration slice, separately per crop (chilli is far more volatile than paddy)."""
import numpy as np


def interval_offsets(residuals, alpha: float = 0.2) -> tuple[float, float]:
    """Lower/upper offsets so that [pred+lo, pred+hi] covers ~(1-alpha) of outcomes."""
    r = np.asarray(residuals, dtype=float)
    return float(np.quantile(r, alpha / 2)), float(np.quantile(r, 1 - alpha / 2))


def fit_conformal(crops, residuals, alpha: float = 0.2) -> dict:
    crops, residuals = np.asarray(crops), np.asarray(residuals, dtype=float)
    out = {"global": interval_offsets(residuals, alpha), "by_crop": {}}
    for c in np.unique(crops):
        r = residuals[crops == c]
        if len(r) >= 50:
            out["by_crop"][str(c)] = interval_offsets(r, alpha)
    return out


def offsets_for(conformal: dict, crop: str) -> tuple[float, float]:
    return conformal["by_crop"].get(crop, conformal["global"])
