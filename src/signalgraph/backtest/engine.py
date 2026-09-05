"""Dislocation backtest engine scaffolding.

This engine supports a research workflow once a signal has been established.
It does NOT optimize thresholds for profitability and ships with no claim of alpha.

Signal (example):
    long direct market when D_t > threshold
    short direct market when D_t < -threshold

Execution:
    buys fill at ask (+ slippage); sells fill at bid (- slippage).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import polars as pl

from signalgraph.backtest.costs import (
    CostModel,
    apply_costs,
    executable_buy_price,
    executable_sell_price,
)
from signalgraph.backtest.metrics import BacktestMetrics, compute_backtest_metrics

ExitRule = Literal["fixed_horizon", "discrepancy_closes"]


@dataclass(frozen=True)
class BacktestConfig:
    threshold: float = 0.02
    exit_rule: ExitRule = "fixed_horizon"
    horizon_steps: int = 15
    discrepancy_exit_level: float = 0.0
    cost_model: CostModel = field(default_factory=CostModel)
    notional_per_trade: float = 1.0


@dataclass
class Trade:
    entry_idx: int
    exit_idx: int
    side: Literal["long", "short"]
    entry_price: float
    exit_price: float
    gross_pnl: float
    net_pnl: float
    holding_time: float


@dataclass
class BacktestResult:
    trades: list[Trade]
    metrics: BacktestMetrics


class BacktestEngine:
    """Chronological dislocation backtest using executable bid/ask prices."""

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()

    def run(
        self,
        frame: pl.DataFrame,
        *,
        dislocation_col: str = "dislocation",
        yes_bid_col: str = "yes_bid",
        yes_ask_col: str = "yes_ask",
    ) -> BacktestResult:
        """Run a simple single-position chronological backtest.

        Required columns: dislocation, yes_bid, yes_ask (for the traded market).
        Frame must already be sorted by timestamp ascending.
        """
        required = {dislocation_col, yes_bid_col, yes_ask_col}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Backtest frame missing columns: {sorted(missing)}")

        data = frame.sort("timestamp") if "timestamp" in frame.columns else frame
        d = data[dislocation_col].to_list()
        bids = data[yes_bid_col].to_list()
        asks = data[yes_ask_col].to_list()
        n = len(d)
        trades: list[Trade] = []
        i = 0
        cfg = self.config

        while i < n:
            di = d[i]
            if di is None or bids[i] is None or asks[i] is None:
                i += 1
                continue

            side: Literal["long", "short"] | None = None
            if di > cfg.threshold:
                side = "long"
            elif di < -cfg.threshold:
                side = "short"
            if side is None:
                i += 1
                continue

            if side == "long":
                entry_price = executable_buy_price(asks[i], cfg.cost_model.slippage)
            else:
                entry_price = executable_sell_price(bids[i], cfg.cost_model.slippage)

            exit_idx = self._find_exit(d, i, side)
            if exit_idx is None or exit_idx >= n:
                break
            if bids[exit_idx] is None or asks[exit_idx] is None:
                i = exit_idx + 1
                continue

            if side == "long":
                exit_price = executable_sell_price(bids[exit_idx], cfg.cost_model.slippage)
                gross = (exit_price - entry_price) * cfg.notional_per_trade
            else:
                exit_price = executable_buy_price(asks[exit_idx], cfg.cost_model.slippage)
                gross = (entry_price - exit_price) * cfg.notional_per_trade

            net = apply_costs(
                gross,
                notional=cfg.notional_per_trade,
                cost_model=cfg.cost_model,
            )
            trades.append(
                Trade(
                    entry_idx=i,
                    exit_idx=exit_idx,
                    side=side,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    gross_pnl=gross,
                    net_pnl=net,
                    holding_time=float(exit_idx - i),
                )
            )
            i = exit_idx + 1

        metrics = compute_backtest_metrics(
            trade_pnls_gross=[t.gross_pnl for t in trades],
            trade_pnls_net=[t.net_pnl for t in trades],
            holding_times=[t.holding_time for t in trades],
            turnover=float(len(trades) * cfg.notional_per_trade * 2),
        )
        return BacktestResult(trades=trades, metrics=metrics)

    def _find_exit(
        self,
        dislocations: list[float | None],
        entry_idx: int,
        side: Literal["long", "short"],
    ) -> int | None:
        cfg = self.config
        if cfg.exit_rule == "fixed_horizon":
            exit_idx = entry_idx + cfg.horizon_steps
            return exit_idx if exit_idx < len(dislocations) else None

        # discrepancy_closes: exit when dislocation crosses toward zero.
        for j in range(entry_idx + 1, len(dislocations)):
            dj = dislocations[j]
            if dj is None:
                continue
            if side == "long" and dj <= cfg.discrepancy_exit_level:
                return j
            if side == "short" and dj >= -cfg.discrepancy_exit_level:
                return j
        return None
