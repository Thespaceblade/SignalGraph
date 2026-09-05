"""Tests for bid/ask execution, Monte Carlo determinism, and market groups."""

from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import pytest

from signalgraph.backtest.costs import executable_buy_price, executable_sell_price
from signalgraph.backtest.engine import BacktestConfig, BacktestEngine
from signalgraph.relationships.grouping import load_market_groups
from signalgraph.simulation.correlation import CorrelationSpec
from signalgraph.simulation.monte_carlo import MonteCarloConfig, simulate_aggregate_probability


def test_buy_uses_ask_sell_uses_bid() -> None:
    assert executable_buy_price(0.55, slippage=0.0) == 0.55
    assert executable_sell_price(0.45, slippage=0.0) == 0.45
    assert executable_buy_price(0.55, slippage=0.01) == 0.56
    assert executable_sell_price(0.45, slippage=0.01) == 0.44


def test_backtest_does_not_use_midpoint_execution() -> None:
    # Wide spread: mid would be 0.50; executable prices differ.
    frame = pl.DataFrame(
        {
            "timestamp": [datetime(2024, 1, 1, 0, i, tzinfo=timezone.utc) for i in range(6)],
            "dislocation": [0.05, 0.05, 0.05, 0.0, 0.0, 0.0],
            "yes_bid": [0.40, 0.40, 0.40, 0.48, 0.48, 0.48],
            "yes_ask": [0.60, 0.60, 0.60, 0.52, 0.52, 0.52],
        }
    )
    engine = BacktestEngine(
        BacktestConfig(threshold=0.02, exit_rule="fixed_horizon", horizon_steps=3)
    )
    result = engine.run(frame)
    assert result.trades, "expected at least one trade"
    trade = result.trades[0]
    assert trade.entry_price == 0.60  # ask, not mid 0.50
    assert trade.exit_price == 0.48  # bid, not mid


def test_monte_carlo_deterministic_with_seed() -> None:
    probs = [0.4, 0.5, 0.6, 0.55]
    cfg = MonteCarloConfig(n_simulations=5000, seed=123, threshold=2)
    a = simulate_aggregate_probability(probs, cfg)
    b = simulate_aggregate_probability(probs, cfg)
    assert a.probability == b.probability
    assert a.successes == b.successes


def test_monte_carlo_rejects_invalid_probabilities() -> None:
    with pytest.raises(ValueError):
        simulate_aggregate_probability([0.5, 1.2], MonteCarloConfig(seed=1))


def test_correlation_spec_independent_matrix() -> None:
    mat = CorrelationSpec(mode="independent").build_matrix(3)
    assert mat.shape == (3, 3)
    assert mat[0, 1] == 0.0
    assert mat[1, 1] == 1.0


def test_market_groups_parsing() -> None:
    path = Path(__file__).resolve().parents[1] / "config" / "market_groups.yaml"
    groups = load_market_groups(path)
    assert "example_aggregate_group" in groups
    g = groups["example_aggregate_group"]
    assert g.relationship_type == "aggregate_constituent"
    assert g.aggregate is not None
    assert g.aggregate.platform == "kalshi"
    assert len(g.constituents) == 3
    # Placeholders should be filtered from "real" refs.
    assert g.real_market_refs() == []


def test_research_universe_group_exists() -> None:
    path = Path(__file__).resolve().parents[1] / "config" / "market_groups.yaml"
    groups = load_market_groups(path)
    assert groups["research_universe_v1"].metadata.get("target_size") == 10
