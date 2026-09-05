# Goals

## Objectives

- Replicate the simplest case of the CME FedWatch tool: the probability of a
  25 bp move vs. no change at the next scheduled FOMC meeting, implied by
  30-Day Fed Funds futures (ZQ).
- Teach how market-implied policy forecasts work: futures settlement rules,
  contract symbology, the day-weighted average identity, and the binary
  outcome model.
- Demonstrate a clean, cost-guarded Databento pull orchestrated with `doit`.

## Success Criteria

- `doit` builds everything from scratch: data pull, unit-tested forecast
  math, two executed notebooks, and the latest-forecast chart.
- The computed probabilities agree with the published FedWatch numbers for
  the same meeting on the same day to within a few percentage points.
- Notebooks run offline from the cached parquet; the only network step is
  the pull.
