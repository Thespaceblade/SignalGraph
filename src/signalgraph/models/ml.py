"""Optional ML model scaffolding.

Do not train models until a statistical relationship is established with
simple baselines and robustness checks. Chronological / walk-forward
validation only — never random shuffles of time-series data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MLPredictor:
    """Placeholder for logistic regression / XGBoost later.

    Intentionally unimplemented to avoid premature model fitting.
    """

    model_type: str = "logistic"
    model: Any = None

    def fit(self, x: Any, y: Any) -> None:
        raise NotImplementedError(
            "ML fitting is deferred until baseline lead-lag / dislocation "
            "research establishes a plausible signal with chronological validation. "
            f"Requested model_type={self.model_type!r}."
        )

    def predict(self, x: Any) -> Any:
        raise NotImplementedError("MLPredictor has not been trained.")
