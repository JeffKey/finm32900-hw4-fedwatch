"""Pull the daily effective federal funds rate (EFFR) from FRED.

The published CME FedWatch tool anchors its forecast to the realized EFFR
published by the New York Fed, rather than to a futures price, and this
project does the same (see notebook 02 and ``fedwatch_monitor.py``):
realized EFFR carries essentially no market noise, and it stays valid even
when the month before a meeting contains a meeting of its own.

The pull uses FRED's public ``fredgraph.csv`` endpoint, which requires no
API key. EFFR is published by the New York Fed each business day at about
9am ET, covering the *previous* business day; FRED mirrors it the same
morning. So the latest observation is one business day behind — the same
one-day lag as the daily futures bars.

Follows the project convention: ``pull_*`` hits the network and, when run as
a script, caches to ``DATA_DIR``; ``load_*`` reads the cache. Refresh with::

    doit forget pull && doit
"""

import io
from pathlib import Path

import pandas as pd
import requests

from settings import config

DATA_DIR = config("DATA_DIR")
START_DATE = config("START_DATE")
END_DATE = config("END_DATE")

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
SERIES = "EFFR"
PARQUET_NAME = "effr.parquet"


def parse_fred_csv(text):
    """Parse a fredgraph.csv payload into a tidy DataFrame [date, effr].

    The first column is the observation date (FRED has named it both DATE
    and observation_date over the years); missing values are ".".
    """
    df = pd.read_csv(io.StringIO(text))
    df.columns = ["date", "effr"]
    df["date"] = pd.to_datetime(df["date"])
    df["effr"] = pd.to_numeric(df["effr"], errors="coerce")
    return df.dropna(subset=["effr"]).reset_index(drop=True)


def pull_effr(start_date=START_DATE, end_date=END_DATE):
    """Pull daily EFFR from FRED (no API key required).

    Returns a DataFrame with columns [date, effr]; effr is in percent
    (e.g. 4.33), matching the units of the futures-implied rates.
    """
    params = {"id": SERIES, "cosd": str(start_date), "coed": str(end_date)}
    response = requests.get(FRED_CSV_URL, params=params, timeout=30)
    response.raise_for_status()
    df = parse_fred_csv(response.text)
    if df.empty:
        raise ValueError(
            f"FRED returned no EFFR observations between {start_date} and "
            f"{end_date}. Check the dates and https://fred.stlouisfed.org/series/EFFR"
        )
    return df


def load_effr(data_dir=DATA_DIR):
    """Load the cached EFFR series pulled by this module."""
    return pd.read_parquet(Path(data_dir) / PARQUET_NAME)


if __name__ == "__main__":
    df = pull_effr()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(DATA_DIR / PARQUET_NAME)
    print(
        f"Saved {len(df):,} EFFR observations "
        f"({df['date'].min().date()} to {df['date'].max().date()}) "
        f"to {DATA_DIR / PARQUET_NAME}"
    )
