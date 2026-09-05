# Research Hypotheses

## H1: Cross-market information propagation

When related prediction markets receive new information, some markets may update
before others.

**Null:** Price changes in market A have no incremental predictive information
for future price changes in market B.

**Alternative:** Price changes in A systematically predict future price changes
in B at certain horizons.

Baseline model:

```
r_B,t+k = alpha + beta * r_A,t + epsilon
```

Horizons of interest: 1, 5, 15, 30, 60 minutes (via resampling / lag steps).

Report: beta, SE, t-stat, CI, correlation, R², N, out-of-sample stability.

Statistical significance ≠ economic meaningfulness.

## H2: Aggregate-constituent dislocations

Synthetic probabilities derived from constituent markets may temporarily diverge
from directly traded aggregate probabilities.

Define:

```
D_t = P_synthetic,t - P_direct,t
```

**Null:** The discrepancy has no predictive relationship with subsequent
convergence.

**Alternative:** Large discrepancies predict future movement in the directly
traded market toward the synthetic estimate.

Correlation among constituents is an explicit research concern—do not assume
independence by default without documenting the assumption.

## H3: Apparent effects may be explained by market microstructure

Observed lead-lag relationships may disappear after controlling for bid/ask
spread, liquidity, volume, stale pricing, and sampling frequency.

This hypothesis is important because **disproving naive alpha is a valid
outcome**.

## Status

No empirical results yet. Populate `findings.md` only after running analyses on
real ingested data.
