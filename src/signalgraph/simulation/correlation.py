"""Correlation handling for constituent-event simulation.

Independence is a transparent baseline only. Real elections / related events
are typically correlated; treating correlation as an explicit research concern
is required before interpreting synthetic dislocations.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CorrelationSpec:
    """Specification for pairwise correlation among constituent Bernoulli events.

    mode:
      - independent: identity correlation (default baseline)
      - constant: all off-diagonal entries equal `rho`
      - custom: use provided matrix
    """

    mode: str = "independent"
    rho: float = 0.0
    matrix: np.ndarray | None = None

    def build_matrix(self, n: int) -> np.ndarray:
        if n < 1:
            raise ValueError("n must be >= 1")
        if self.mode == "independent":
            return independent_correlation_matrix(n)
        if self.mode == "constant":
            if not -1.0 <= self.rho <= 1.0:
                raise ValueError("rho must be in [-1, 1]")
            mat = np.full((n, n), self.rho, dtype=float)
            np.fill_diagonal(mat, 1.0)
            return mat
        if self.mode == "custom":
            if self.matrix is None:
                raise ValueError("custom mode requires matrix")
            mat = np.asarray(self.matrix, dtype=float)
            if mat.shape != (n, n):
                raise ValueError(f"matrix shape must be {(n, n)}; got {mat.shape}")
            return mat
        raise ValueError(f"Unknown correlation mode: {self.mode}")


def independent_correlation_matrix(n: int) -> np.ndarray:
    return np.eye(n, dtype=float)
