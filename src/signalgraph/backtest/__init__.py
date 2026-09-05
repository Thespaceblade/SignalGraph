"""Backtesting framework scaffolding — not a profitable strategy."""

from signalgraph.backtest.engine import BacktestConfig, BacktestEngine, BacktestResult
from signalgraph.backtest.costs import CostModel, apply_costs
from signalgraph.backtest.metrics import compute_backtest_metrics

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestResult",
    "CostModel",
    "apply_costs",
    "compute_backtest_metrics",
]
