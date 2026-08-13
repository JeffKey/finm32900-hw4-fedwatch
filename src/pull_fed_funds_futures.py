"""Pull daily 30-Day Fed Funds futures (ZQ) bars from Databento.

Uses the CME Globex dataset (GLBX.MDP3) with parent symbology (``ZQ.FUT``),
which returns every listed ZQ contract -- the outright monthly contracts we
need plus calendar spreads (filtered downstream by ``fedwatch``). The
``ohlcv-1d`` schema gives one bar per contract per trading day.

Everything this project pulls is covered by the course's Databento
subscription, so downloading it is free. As a safety net, every query is
priced with the free ``metadata.get_cost`` endpoint first, and the pull
refuses to download anything whose estimate is not $0.00 -- so running
this script can never incur a charge.

Follows the project convention: ``pull_*`` hits the network and, when run as
a script, caches to ``DATA_DIR``; ``load_*`` reads the cache. Refresh with::

    doit forget pull && doit
"""

from pathlib import Path

import pandas as pd

from settings import config

DATA_DIR = config("DATA_DIR")
START_DATE = config("START_DATE")
END_DATE = config("END_DATE")
DATABENTO_API_KEY = config("DATABENTO_API_KEY", default="")

DATASET = "GLBX.MDP3"
SYMBOLS = ["ZQ.FUT"]  # parent symbology: all listed 30-Day Fed Funds contracts
STYPE_IN = "parent"
SCHEMA = "ohlcv-1d"
PARQUET_NAME = "fed_funds_futures.parquet"


def build_query(start_date=START_DATE, end_date=END_DATE):
    """The same dict feeds get_cost and get_range, so the cost guard always
    prices exactly the query that is pulled."""
    return dict(
        dataset=DATASET,
        symbols=SYMBOLS,
        stype_in=STYPE_IN,
        schema=SCHEMA,
        start=start_date,
        end=end_date,
    )


def clamp_end_date(client, end_date):
    """Clamp the requested end date to what the dataset actually has.

    Historical data lags real time by about a day; asking past the available
    end raises, so we clamp instead of guessing "yesterday".
    """
    available_end = pd.Timestamp(client.metadata.get_dataset_range(DATASET)["end"])
    if available_end.tzinfo is not None:
        available_end = available_end.tz_convert("UTC").tz_localize(None)
    end = min(pd.Timestamp(end_date), available_end)
    return end.strftime("%Y-%m-%d")


def assert_query_is_free(cost):
    """Abort (SystemExit) unless Databento's estimate for the query is $0.00.

    DO NOT MODIFY OR BYPASS THIS GUARD. Everything this project pulls is
    covered by the course's CME Globex subscription, so the estimate should
    always be $0.00. If it is not -- the query was edited, or the API key
    belongs to an account without the subscription -- we stop before
    downloading anything, so no run of this script ever spends money.
    """
    print(f"Databento cost estimate for this query: ${cost:,.2f}")
    if cost > 0:
        print(
            f"\nABORTING: the estimate is ${cost:,.4f}, but everything this "
            "project pulls should be free ($0.00) under the course's Databento "
            "subscription. Nothing was downloaded and nothing was charged.\n"
            "Check that your API key belongs to an account covered by the "
            "course subscription and that the query (dataset, schema, symbols, "
            "dates) has not been modified."
        )
        raise SystemExit(1)


def pull_fed_funds_futures(start_date=START_DATE, end_date=END_DATE):
    """Pull daily ZQ bars, returning a tidy DataFrame.

    Columns: date (tz-naive trading date), symbol, open, high, low, close,
    volume. Includes calendar-spread symbols; filter with
    ``fedwatch.filter_outright_contracts``.
    """
    import databento as db

    client = db.Historical(key=DATABENTO_API_KEY)
    query = build_query(start_date, clamp_end_date(client, end_date))

    cost = client.metadata.get_cost(**query)
    assert_query_is_free(cost)

    data = client.timeseries.get_range(**query)
    df = data.to_df().reset_index()
    # ohlcv-1d bars are stamped 00:00 UTC of the trading date
    df["date"] = df["ts_event"].dt.tz_convert("UTC").dt.normalize().dt.tz_localize(None)
    return df[["date", "symbol", "open", "high", "low", "close", "volume"]]


def load_fed_funds_futures(data_dir=DATA_DIR):
    """Load the cached ZQ daily bars pulled by this module."""
    return pd.read_parquet(Path(data_dir) / PARQUET_NAME)


if __name__ == "__main__":
    if not DATABENTO_API_KEY:
        raise SystemExit(
            "DATABENTO_API_KEY is not set. Copy .env.example to .env and add "
            "your key (https://databento.com, Account > API keys)."
        )
    df = pull_fed_funds_futures()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(DATA_DIR / PARQUET_NAME)
    print(
        f"Saved {len(df):,} rows for {df['symbol'].nunique()} symbols "
        f"({df['date'].min().date()} to {df['date'].max().date()}) "
        f"to {DATA_DIR / PARQUET_NAME}"
    )
