"""Simple statistical baselines (no trained ML yet)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from signalgraph.research.regression import RegressionResult, ols_regression


@dataclass
class BaselinePredictor:
    """Univariate linear baseline: y = alpha + beta x.

    Use only with chronological splits. Do not shuffle time-series rows.
    """

    result: RegressionResult | None = None

    def fit(self, x: np.ndarray, y: np.ndarray) -> RegressionResult:
        self.result = ols_regression(y, x)
        return self.result

    def predict(self, x: np.ndarray) -> np.ndarray:
        if self.result is None:
            raise RuntimeError("BaselinePredictor must be fit before predict()")
        x = np.asarray(x, dtype=float)
        return self.result.alpha + self.result.coefficient * x
