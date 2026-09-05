"""Monte Carlo simulation scaffolding for synthetic aggregate probabilities."""

from signalgraph.simulation.monte_carlo import (
    MonteCarloConfig,
    simulate_aggregate_probability,
)
from signalgraph.simulation.correlation import CorrelationSpec, independent_correlation_matrix

__all__ = [
    "MonteCarloConfig",
    "simulate_aggregate_probability",
    "CorrelationSpec",
    "independent_correlation_matrix",
]
