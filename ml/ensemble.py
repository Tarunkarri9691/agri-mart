"""ML ensemble (patent FIG. 5, model 520): XGBoost + RandomForest + HistGradientBoosting, averaged."""
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from xgboost import XGBRegressor


class Ensemble:
    def __init__(self, seed: int = 42):
        self.members = {
            "xgboost": XGBRegressor(n_estimators=250, max_depth=5, learning_rate=0.05, subsample=0.8,
                                    colsample_bytree=0.8, random_state=seed, n_jobs=-1),
            "random_forest": RandomForestRegressor(n_estimators=100, min_samples_leaf=5, n_jobs=-1, random_state=seed),
            "hist_gbm": HistGradientBoostingRegressor(max_iter=200, learning_rate=0.06, random_state=seed),
        }

    def fit(self, X, y):
        for m in self.members.values():
            m.fit(X, y)
        return self

    def predict_members(self, X) -> dict:
        return {n: m.predict(X) for n, m in self.members.items()}

    def predict(self, X):
        return np.mean(list(self.predict_members(X).values()), axis=0)

    @property
    def xgb(self):
        return self.members["xgboost"]
