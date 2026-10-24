# Project Overview

## Case Study - FedWatch Replication

This case study replicates the simplest case of the
[CME FedWatch tool](https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html):
the market-implied probability of the *next* FOMC rate decision, backed out of
30-Day Fed Funds futures (ZQ) prices pulled from Databento. Two teaching
notebooks walk through the futures data and the probability math, and the
pipeline renders a FedWatch-style chart of the latest forecast.

| Section | Description |
|---------|-------------|
| Goals | Project objectives and success criteria |
| Data Sources | Description of datasets and how they are obtained |
| Methodology | Approach, methods, and implementation details |

```{toctree}
:maxdepth: 1
:caption: Project Details

project_overview/goals
project_overview/data_sources
project_overview/methodology
```
