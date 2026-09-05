"""Backtest performance metrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class BacktestMetrics:
    gross_pnl: float
    net_pnl: float
    average_return_per_trade: float
    hit_rate: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    turnover: float
    number_of_trades: int
    average_holding_time: float

    def to_dict(self) -> dict:
        return asdict(self)


def max_drawdown(equity_curve: np.ndarray) -> float:
    if equity_curve.size == 0:
        return float("nan")
    peaks = np.maximum.accumulate(equity_curve)
    drawdowns = equity_curve - peaks
    return float(drawdowns.min())


def compute_backtest_metrics(
    *,
    trade_pnls_gross: list[float] | np.ndarray,
    trade_pnls_net: list[float] | np.ndarray,
    holding_times: list[float] | np.ndarray,
    turnover: float = 0.0,
    periods_per_year: float = 365.25 * 24 * 60,
) -> BacktestMetrics:
    """Compute summary metrics from realized trades.

    Sharpe uses net per-trade returns with a naive annualization factor.
    This is descriptive only — not a claim of tradable edge.
    """
    gross = np.asarray(trade_pnls_gross, dtype=float)
    net = np.asarray(trade_pnls_net, dtype=float)
    holds = np.asarray(holding_times, dtype=float)
    n = int(net.size)
    if n == 0:
        return BacktestMetrics(
            gross_pnl=0.0,
            net_pnl=0.0,
            average_return_per_trade=float("nan"),
            hit_rate=float("nan"),
            volatility=float("nan"),
            sharpe_ratio=float("nan"),
            max_drawdown=float("nan"),
            turnover=float(turnover),
            number_of_trades=0,
            average_holding_time=float("nan"),
        )

    equity = np.cumsum(net)
    vol = float(np.std(net, ddof=1)) if n > 1 else float("nan")
    mean_net = float(np.mean(net))
    sharpe = float("nan")
    if n > 1 and vol > 0:
        sharpe = (mean_net / vol) * np.sqrt(periods_per_year)

    return BacktestMetrics(
        gross_pnl=float(np.sum(gross)),
        net_pnl=float(np.sum(net)),
        average_return_per_trade=mean_net,
        hit_rate=float(np.mean(net > 0)),
        volatility=vol,
        sharpe_ratio=sharpe,
        max_drawdown=max_drawdown(equity),
        turnover=float(turnover),
        number_of_trades=n,
        average_holding_time=float(np.mean(holds)) if holds.size else float("nan"),
    )
