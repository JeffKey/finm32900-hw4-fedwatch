# Dataframe: `JeffKey/finm32900_hw4_fedwatch:fed_funds_futures` - 30-Day Fed Funds Futures Daily Bars (Databento)

Daily bars from Databento's GLBX.MDP3 dataset (schema `ohlcv-1d`,
parent symbol `ZQ.FUT`). Includes outright monthly contracts and calendar
spreads; filter with `fedwatch.filter_outright_contracts`. Prices are in index
points; the implied average fed funds rate for a contract month is 100 minus
the price. Refresh with `doit forget pull && doit`.


## DataFrame Glimpse

```
Rows: 12207
Columns: 7
$ date   <datetime[ns]> 2026-09-04 00:00:00
$ symbol          <str> 'ZQN7-ZQQ7'
$ open            <f64> 1.0
$ high            <f64> 1.5
$ low             <f64> 1.0
$ close           <f64> 1.0
$ volume          <u64> 2345


```

## Dataframe Manifest

| Dataframe Name                 | 30-Day Fed Funds Futures Daily Bars (Databento)                                                          |
|--------------------------------|--------------------------------------------------------------------------------------|
| Dataframe ID                   | [fed_funds_futures](../dataframes/JeffKey--finm32900_hw4_fedwatch/fed_funds_futures.md)                                       |
| Sources                        |                                           |
| Providers                      |                                         |
| Provider Links                 |                                    |
| Tags                           | Monetary Policy, Futures, Databento                                             |
| Access Types                   |                                       |
| How is data pulled?            | Databento Historical API via src/pull_fed_funds_futures.py (cost-guarded)                                                   |
| Data available up to (min)     | 2026-09-04 00:00:00                                                             |
| Data available up to (max)     | 2026-09-04 00:00:00                                                             |
| Dataframe Path                 | /home/runner/work/finm32900-hw4-fedwatch/finm32900-hw4-fedwatch/_data/fed_funds_futures.parquet                                             |


**Linked Charts:**


- [JeffKey/finm32900_hw4_fedwatch:fedwatch_latest_forecast](../../charts/JeffKey--finm32900_hw4_fedwatch.fedwatch_latest_forecast.md)



## Pipeline Manifest

| Pipeline Name                   | HW 4 - FedWatch Monitor                       |
|---------------------------------|--------------------------------------------------------|
| Pipeline ID                     | [JeffKey/finm32900_hw4_fedwatch](../../../index.md)              |
| Maintainer                      | Jeremiah Bejarano               |
| Contributors                    | Jeremiah Bejarano |
| Repository                     |                   |
| Pipeline Web Page               | <a href="file:///home/runner/work/finm32900-hw4-fedwatch/finm32900-hw4-fedwatch/docs/index.html">Pipeline Web Page      |
| Date of Last Code Update        | 2026-09-05 11:53:39           |
| OS Compatibility                | Windows, Linux, macOS |
| Linked Dataframes               |  [JeffKey/finm32900_hw4_fedwatch:fed_funds_futures](../../dataframes/JeffKey--finm32900_hw4_fedwatch/fed_funds_futures.md)<br>  |


**Build Commands:**
```
doit

```

