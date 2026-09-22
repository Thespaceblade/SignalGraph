# SignalGraph Quant Research Roadmap

## Project Objective

**Primary question:**

> Do logically related prediction markets incorporate information at different speeds, creating temporary probability dislocations that predict future convergence?

We are **not** assuming this effect exists.

The goal is to determine whether it exists.

---

# Phase 0: Freeze the Engineering

## Goal

Stop building infrastructure unless the research genuinely requires it.

Right now, do **not** work on:

- Frontend
- XGBoost
- Neural networks
- Polymarket integration
- Automated trading
- Portfolio optimization
- Fancy dashboards
- FastAPI
- Deployment

The repo already contains enough infrastructure to begin research.

## Rule

> Every new piece of code must answer a research question.

---

# Phase 1: Define the First Hypothesis

Before downloading data, write the hypothesis yourself.

## H1: Lead-Lag Behavior

Suppose markets \(A\) and \(B\) are logically connected.

Define:

\[
p_{A,t}
\]

as market A's implied probability at time \(t\).

Define:

\[
\Delta p_{A,t}=p_{A,t}-p_{A,t-1}
\]

Test whether:

\[
\Delta p_{A,t}
\]

contains information about:

\[
\Delta p_{B,t+k}
\]

for some future horizon \(k\).

## Null Hypothesis

\[
H_0:\beta=0
\]

Movement in A provides no information about future movement in B.

## Alternative Hypothesis

\[
H_1:\beta\neq0
\]

Movement in A systematically precedes movement in B.

## Your Task

Write 2-3 paragraphs in:

```text
research/hypotheses.md
```

explaining **why you think this could happen economically**.

Example:

> More liquid constituent markets may respond to information faster than broader aggregate markets.

Do this **before seeing results**.

This prevents yourself from inventing explanations afterward.

---

# Phase 2: Choose One Market Universe

Do not grab hundreds of random Kalshi contracts.

Choose approximately:

```text
5-15 related markets
```

Ideally:

- One aggregate event
- Several constituent events

## Possible Example: Politics

```text
Senate Control
├── NC Senate
├── GA Senate
├── ME Senate
├── OH Senate
└── TX Senate
```

## Possible Example: Sports

```text
NBA Championship
├── Eastern Conference Champion
├── Western Conference Champion
├── Team A Championship
├── Team B Championship
└── Team C Championship
```

## Possible Example: Economics

Use related markets involving:

- Federal Reserve decisions
- Inflation
- Unemployment
- GDP
- Recession outcomes

## Selection Criteria

Markets should:

- Have real trading activity
- Have meaningful historical price movement
- Overlap substantially in time
- Be logically connected
- Preferably differ somewhat in liquidity

Liquidity differences may themselves generate interesting information-flow behavior.

---

# Phase 3: Understand the Contracts Manually

Before writing analysis code, read the exact settlement conditions for every contract.

Create a table like:

| Market | Meaning | Opens | Resolves | Relationship |
|---|---|---|---|---|
| A | Senate control | ... | ... | Aggregate |
| B | NC winner | ... | ... | Constituent |

Ask:

> What exact event causes YES to pay $1?

Two markets that sound related may have subtly different settlement conditions.

## Quant Rule

> Never model a financial instrument whose payoff you do not understand.

---

# Phase 4: Acquire Raw Data

Use the existing Kalshi ingestion layer.

For every market, collect:

```text
timestamp
bid
ask
mid
last trade
volume
open interest
```

Keep the original API response.

Do **not** immediately transform everything.

Preserve:

```text
data/raw/
```

as your immutable source.

## Goal

At the end of this phase:

> I can reproduce my dataset from the source.

---

# Phase 5: Audit the Data

Before statistics, interrogate the dataset.

For each market calculate:

```text
number of observations
start timestamp
end timestamp
missingness
average spread
median spread
volume
frequency of price updates
percentage of unchanged intervals
```

Ask:

- Does one market trade every minute while another sits unchanged for 40 minutes?
- Does one have a 1¢ spread while another has a 12¢ spread?
- Are some markets extremely illiquid?
- Are there long periods of stale quotes?

These differences may explain apparent lead-lag relationships.

This is **market microstructure**.

Write observations down.

---

# Phase 6: Plot Everything

Plot:

\[
p_{i,t}
\]

for every related market.

Then plot probability changes.

Look manually for episodes like:

```text
Market A jumps
      ↓
Market B stays flat
      ↓
Market B moves 10 minutes later
```

Ask:

> Does the phenomenon I'm proposing even appear visually?

Also look for counterexamples.

Do not search only for confirmation.

---

# Phase 7: Define the Time Grid

Align markets at different frequencies.

Try:

```text
1 minute
5 minutes
15 minutes
60 minutes
```

Forward filling assumes:

> The most recently observed market price remains our best available price until another observation arrives.

This is reasonable, but it creates another issue:

## Stale Prices

Track:

\[
AgeOfPrice_t
\]

Meaning:

> How long ago was this market's last actual update?

This may become an important control variable.

---

# Phase 8: Establish Descriptive Statistics

Before regression, calculate simple relationships.

For every pair:

\[
corr(\Delta p_A,\Delta p_B)
\]

Then:

\[
corr(\Delta p_{A,t},\Delta p_{B,t+1})
\]

\[
corr(\Delta p_{A,t},\Delta p_{B,t+5})
\]

and so on.

Build a matrix like:

| Source | Target | 1m | 5m | 15m | 60m |
|---|---|---:|---:|---:|---:|
| NC | Control | .02 | .11 | .16 | .04 |
| GA | Control | .01 | .07 | .09 | .02 |

Do not declare victory.

You are only looking for structure.

---

# Phase 9: Run the Baseline Regression

Use:

\[
\Delta p_{B,t+k}
=
\alpha+\beta\Delta p_{A,t}+\epsilon_t
\]

Record:

- Coefficient
- Standard error
- t-statistic
- p-value
- \(R^2\)
- Observations
- Correlation

Suppose:

\[
\beta=.18
\]

with:

\[
p=.003
\]

Your reaction should **not** be:

> Alpha found.

Your reaction should be:

> Interesting. Why might this be fake?

That is the quant mindset.

---

# Phase 10: Try to Destroy the Result

This is one of the most important phases of SignalGraph.

## Test 1: Spread

Does the relationship disappear when spreads are small?

If so, the apparent signal may come from stale quotes.

---

## Test 2: Liquidity

Condition on high-liquidity periods.

Does A still lead B?

---

## Test 3: Volume

Maybe A moves first simply because trading happens there first.

Include recent volume as a control.

---

## Test 4: Price Staleness

Calculate:

\[
timeSinceLastUpdate
\]

A market sitting unchanged is not necessarily disagreeing with another market.

It may simply have nobody trading it.

---

## Test 5: Sampling Frequency

Repeat the analysis at:

```text
1m
5m
15m
60m
```

If the effect exists only at exactly one arbitrary frequency, be suspicious.

---

## Test 6: Time Period

Split chronologically.

Example:

```text
First 60%   Discovery
Next 20%    Validation
Last 20%    Untouched Test
```

Do not randomly shuffle time-series data.

---

# Phase 11: Deal With Multiple Hypothesis Testing

Suppose you have:

\[
10
\]

markets.

That gives as many as:

\[
90
\]

directional market pairs.

Then test:

```text
1m
5m
15m
30m
60m
```

Now you may have:

\[
90\times5=450
\]

statistical tests.

At:

\[
p<0.05
\]

you would expect roughly:

\[
450(0.05)=22.5
\]

apparently significant findings **by chance**.

Implement something such as:

## Benjamini-Hochberg False Discovery Rate

Then see which relationships survive correction.

This is an important part of making the project statistically credible.

---

# Phase 12: Construct the Market Graph

Now SignalGraph earns its name.

Define nodes:

\[
V=\{\text{prediction markets}\}
\]

Define directed edges:

\[
A\rightarrow B
\]

when A exhibits robust lead-lag behavior toward B.

Edge weight could represent:

\[
\beta
\]

or out-of-sample predictive strength.

Example:

```text
NC ───────→ Senate Control

GA ───→ Senate Control

ME ─────────→ Senate Control
```

Now ask:

> Which markets appear to act as information leaders?

This becomes a genuinely interesting research question.

---

# Phase 13: Move to Synthetic Probabilities

Only do this when you have an aggregate-constituent relationship where the mathematics makes sense.

Suppose:

\[
p_1,p_2,\ldots,p_n
\]

represent constituent probabilities.

Use Monte Carlo simulation to estimate:

\[
P_{\text{synthetic}}(\text{aggregate event})
\]

Then compare it against:

\[
P_{\text{direct}}
\]

Define:

\[
D_t=P_{\text{synthetic},t}-P_{\text{direct},t}
\]

This is your **dislocation measure**.

---

# Phase 14: Question the Monte Carlo Assumptions

This is where the research gets harder.

Your baseline simulation may assume independence.

But political races, sports outcomes, and economic events are often correlated.

Ask:

> What common latent variable affects all these outcomes?

For politics, this might be:

\[
Z=\text{national political environment}
\]

Conceptually:

\[
P(Y_i=1)
=
\sigma(X_i\beta+\lambda_iZ)
\]

You do not necessarily need an extremely complicated model.

But you must document:

> What assumptions generate my synthetic probability?

Otherwise:

\[
P_{\text{synthetic}}
\]

does not mean very much.

---

# Phase 15: Test Convergence

Now test the project's central question.

Does:

\[
D_t
\]

predict:

\[
\Delta P_{\text{direct},t+k}
\]

?

Regression:

\[
\Delta P_{\text{direct},t+k}
=
\alpha+\beta D_t+\epsilon_t
\]

If:

\[
D_t>0
\]

and direct markets subsequently rise, that is evidence of convergence.

Investigate:

- Different horizons
- Different regimes
- Different liquidity levels
- Out-of-sample performance

---

# Phase 16: Freeze the Hypothesis

If you find something interesting, stop changing it.

Write down:

```text
Signal definition
Threshold
Markets included
Sampling frequency
Holding period
Controls
```

Freeze them.

Now evaluate on the untouched test period.

This approximates:

> What would have happened if I had actually discovered this at the time?

---

# Phase 17: Only Now Backtest

Test something simple.

Example:

\[
D_t>5\%
\]

Buy YES.

If:

\[
D_t<-5\%
\]

Sell YES or buy NO depending on market mechanics.

Possible exit rules:

```text
30 minutes
1 hour
dislocation closes
```

Report:

```text
gross PnL
net PnL
number of trades
hit rate
Sharpe ratio
max drawdown
turnover
average holding period
```

The most important number is:

\[
\boxed{\text{Net PnL after realistic costs}}
\]

Use realistic:

- Bid prices
- Ask prices
- Fees
- Slippage
- Liquidity assumptions

Do not assume midpoint execution.

---

# Phase 18: Sensitivity Analysis

Try reasonable parameter variations.

If your strategy works at:

```text
4%
5%
6%
```

that is encouraging.

If:

```text
4.9%  → loses money
5.0%  → huge profits
5.1%  → loses money
```

you probably overfit.

Do the same for:

- Holding periods
- Sampling frequencies
- Market subsets
- Liquidity thresholds

You want a **region of reasonable performance**, not one magical parameter.

---

# Phase 19: Only Now Consider Machine Learning

Machine learning should answer:

> Can additional observable information improve the simple dislocation signal?

Possible features:

\[
X_t=
[
D_t,
spread_t,
volume_t,
liquidity_t,
priceAge_t,
momentum_t,
relatedMarketMoves_t
]
\]

Possible target:

\[
Y_t=\Delta P_{t+30m}
\]

Start with:

1. Linear regression
2. Logistic regression

Then maybe:

3. Gradient boosting

Your baseline should remain:

\[
\hat{Y}=f(D_t)
\]

If XGBoost does not beat the simple baseline out of sample:

> Do not use XGBoost.

That is still a valid research result.

---

# Phase 20: Write the Research Conclusion

Your final project should not claim:

> Built profitable prediction-market AI.

Instead, describe what you actually tested.

Example:

> Investigated whether information propagates asynchronously across logically related prediction markets using timestamped Kalshi data. Tested lead-lag relationships across multiple horizons, controlled for liquidity and spread effects, corrected for multiple comparisons, modeled aggregate probabilities using constituent-market simulations, and evaluated surviving dislocations out of sample with realistic execution assumptions.

Then report what actually happened.

Failures are valid findings.

A strong conclusion could be:

> Apparent lead-lag relationships largely disappeared after controlling for quote staleness, suggesting many observed prediction-market inefficiencies were microstructure artifacts rather than information advantages.

That is good quantitative research.

---

# Immediate Next Tasks

Do **not** touch ML or the frontend yet.

Complete these first:

## Task 1: Pick a Research Universe

Choose one coherent family of roughly:

```text
5-15 Kalshi markets
```

---

## Task 2: Understand Every Contract

Read the settlement rules manually.

Document what YES and NO actually mean.

---

## Task 3: Populate the Config

Update:

```text
config/market_groups.yaml
```

Populate:

```text
research_universe_v1
```

with the real markets.

---

## Task 4: Download Historical Data

Collect the raw historical observations for the selected markets.

Confirm:

- Timestamps
- Bid
- Ask
- Mid
- Volume
- Liquidity
- Missingness

---

## Task 5: Plot Price Paths

Plot the related market probabilities over time.

Do this **before running a predictive model**.

Ask:

> Do I visually see evidence of asynchronous information movement or temporary disagreement?

---

# Research Mindset

Throughout the entire project, keep asking:

> What would have to be true for this result to be fake?

Possible explanations include:

- Stale quotes
- Wide spreads
- Thin liquidity
- Common news shocks
- Sampling artifacts
- Data leakage
- Multiple testing
- Overfitting
- Incorrect contract relationships
- Unrealistic execution
- Incorrect independence assumptions

The goal is not to prove that the strategy works.

The goal is to determine whether the phenomenon survives serious attempts to disprove it.

---

# End Goal

By the end of SignalGraph, you should be able to confidently explain:

1. Why you chose the research question
2. How prediction-market contracts work
3. How you collected and normalized the data
4. What lead-lag behavior means
5. How you tested statistical significance
6. Why multiple-hypothesis correction matters
7. How liquidity and spreads can create fake signals
8. How you prevented look-ahead bias
9. How you constructed synthetic probabilities
10. What assumptions your simulation makes
11. Whether dislocations predict convergence
12. Whether results survive out-of-sample testing
13. Whether any apparent alpha survives realistic costs
14. What failed
15. What you would investigate next

If you can defend all of those in an interview, SignalGraph is doing its job.
