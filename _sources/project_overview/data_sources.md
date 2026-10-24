# Data Sources

## Overview

Two market data sources plus one small manually-maintained calendar file:
Databento for the futures prices, and FRED for the realized EFFR that
anchors the forecast, as the published FedWatch tool does. Notebooks never
touch the network; they load the cached parquets produced by the pulls.

## Datasets

| Dataset | Source | Frequency | Description |
|---------|--------|-----------|-------------|
| ZQ daily bars | Databento, `GLBX.MDP3` | Daily | OHLCV bars for all listed 30-Day Fed Funds futures contracts (parent symbol `ZQ.FUT`, schema `ohlcv-1d`), trailing ~6 months |
| EFFR | FRED ([EFFR](https://fred.stlouisfed.org/series/EFFR), mirroring the NY Fed; no API key) | Business days | Realized effective federal funds rate, in percent; published each morning for the previous business day. Anchors the forecast as the pre-meeting rate |
| FOMC calendar | [federalreserve.gov](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) | ~8 meetings/yr | Scheduled meeting dates, hand-maintained in `data_manual/fomc_meetings.csv`; must be appended annually (the monitor warns when fewer than ~6 months remain) |

## Data Pipeline

- `src/pull_fed_funds_futures.py` pulls the ZQ bars. The pull is free under
  the course's Databento subscription; the script verifies this with the
  free `metadata.get_cost` endpoint first and refuses to download anything
  whose estimate is not $0.00.
- `src/pull_effr.py` pulls EFFR from FRED's public CSV endpoint (free, no
  API key).
- The pulls write `_data/fed_funds_futures.parquet` and `_data/effr.parquet`;
  refresh with `doit forget pull && doit`.
- `src/fedwatch.py` (pure functions, unit tested) holds the math;
  `src/fedwatch_monitor.py` assembles it into the EFFR-anchored forecast,
  which `src/fedwatch_chart.py` renders to
  `_output/fedwatch_latest_forecast.{png,html}`.
- `doit monitor` is the unattended daily entrypoint: it re-pulls both
  sources, appends the day's snapshot to `_data/fedwatch_history.parquet`,
  rewrites `_output/fedwatch_monitor_latest.csv`, and refreshes the charts.
