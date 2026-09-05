"""Generic OLS helpers for research notebooks and scripts."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import statsmodels.api as sm


@dataclass(frozen=True)
class RegressionResult:
    coefficient: float
    standard_error: float
    t_stat: float
    p_value: float
    r_squared: float
    observations: int
    alpha: float

    def to_dict(self) -> dict:
        return asdict(self)


def ols_regression(y: np.ndarray, x: np.ndarray) -> RegressionResult:
    """Simple univariate OLS with intercept: y = alpha + beta x + e."""
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    mask = np.isfinite(y) & np.isfinite(x)
    y, x = y[mask], x[mask]
    if y.size < 3:
        return RegressionResult(
            coefficient=float("nan"),
            standard_error=float("nan"),
            t_stat=float("nan"),
            p_value=float("nan"),
            r_squared=float("nan"),
            observations=int(y.size),
            alpha=float("nan"),
        )
    exog = sm.add_constant(x)
    model = sm.OLS(y, exog).fit()
    return RegressionResult(
        coefficient=float(model.params[1]),
        standard_error=float(model.bse[1]),
        t_stat=float(model.tvalues[1]),
        p_value=float(model.pvalues[1]),
        r_squared=float(model.rsquared),
        observations=int(model.nobs),
        alpha=float(model.params[0]),
    )
