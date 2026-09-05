"""Lead-lag and related research utilities."""

from signalgraph.research.lead_lag import (
    build_lagged_features,
    lead_lag_correlation,
    run_lead_lag_regression,
    run_multiple_horizons,
    test_multiple_horizons,
)
from signalgraph.research.returns import calculate_probability_change
from signalgraph.research.regression import ols_regression
from signalgraph.research.robustness import RobustnessChecklist
from signalgraph.research.calibration import chronological_split

__all__ = [
    "calculate_probability_change",
    "build_lagged_features",
    "lead_lag_correlation",
    "run_lead_lag_regression",
    "run_multiple_horizons",
    "test_multiple_horizons",
    "ols_regression",
    "RobustnessChecklist",
    "chronological_split",
]
