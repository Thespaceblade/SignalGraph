"""Monte Carlo estimation of synthetic aggregate probabilities.

Initial aggregate rule (explicitly simplistic):
    Aggregate event occurs if the sum of constituent Bernoulli outcomes
    meets or exceeds `threshold` (default: majority / custom).

Correlation:
    Default mode is independent sampling. Gaussian-copula style correlated
    Bernoulli sampling is provided as an interface when a CorrelationSpec
    is supplied — document the assumption when used.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

from signalgraph.simulation.correlation import CorrelationSpec


@dataclass(frozen=True)
class MonteCarloConfig:
    n_simulations: int = 10_000
    threshold: float | None = None  # if None, use majority (> n/2)
    seed: int | None = None
    correlation: CorrelationSpec | None = None


@dataclass(frozen=True)
class MonteCarloResult:
    probability: float
    n_simulations: int
    seed: int | None
    correlation_mode: str
    successes: int


def simulate_aggregate_probability(
    probabilities: list[float] | np.ndarray,
    config: MonteCarloConfig | None = None,
) -> MonteCarloResult:
    """Estimate P(aggregate) from constituent probabilities via simulation.

    Args:
        probabilities: Constituent event probabilities in [0, 1].
        config: Simulation configuration.

    Returns:
        MonteCarloResult with estimated aggregate probability.
    """
    config = config or MonteCarloConfig()
    p = np.asarray(probabilities, dtype=float)
    if p.ndim != 1 or p.size == 0:
        raise ValueError("probabilities must be a non-empty 1-D array")
    if np.any((p < 0.0) | (p > 1.0)):
        raise ValueError("All probabilities must be in [0, 1]")

    corr_spec = config.correlation or CorrelationSpec(mode="independent")
    corr = corr_spec.build_matrix(p.size)
    rng = np.random.default_rng(config.seed)

    threshold = config.threshold
    if threshold is None:
        threshold = (p.size / 2.0) + 1e-12  # strict majority of wins

    if corr_spec.mode == "independent":
        draws = rng.random((config.n_simulations, p.size)) < p
    else:
        # Gaussian copula: correlated normals -> uniforms -> Bernoulli.
        # Requires positive-definite correlation matrix.
        mean = np.zeros(p.size)
        z = rng.multivariate_normal(mean, corr, size=config.n_simulations)
        u = stats.norm.cdf(z)
        draws = u < p

    successes = int(np.sum(draws.sum(axis=1) >= threshold))
    prob = successes / config.n_simulations
    return MonteCarloResult(
        probability=float(prob),
        n_simulations=config.n_simulations,
        seed=config.seed,
        correlation_mode=corr_spec.mode,
        successes=successes,
    )


def dislocation(
    p_synthetic: float,
    p_direct: float,
) -> float:
    """D_t = P_synthetic,t - P_direct,t."""
    return float(p_synthetic) - float(p_direct)
