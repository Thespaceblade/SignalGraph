"""Transaction cost models for realistic backtests.

Do not assume midpoint execution. Buy at ask, sell at bid.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    """Configurable cost assumptions.

    platform_fee_rate: fraction of notional charged by the exchange.
    slippage: additional adverse probability move on entry/exit.
    """

    platform_fee_rate: float = 0.0
    slippage: float = 0.0


def executable_buy_price(yes_ask: float, slippage: float = 0.0) -> float:
    """Price paid to buy YES — ask plus slippage, capped at 1."""
    return min(1.0, float(yes_ask) + float(slippage))


def executable_sell_price(yes_bid: float, slippage: float = 0.0) -> float:
    """Price received to sell YES — bid minus slippage, floored at 0."""
    return max(0.0, float(yes_bid) - float(slippage))


def apply_costs(
    gross_pnl: float,
    *,
    notional: float,
    cost_model: CostModel,
) -> float:
    """Convert gross PnL to net PnL after fees (slippage already in prices)."""
    fees = abs(notional) * cost_model.platform_fee_rate
    return float(gross_pnl) - fees
