"""Core math for market-implied forecasts of the next FOMC decision.

Replicates the simplest case of the CME FedWatch tool
(https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html):
the probability of a rate change at the *next* scheduled FOMC meeting,
implied by 30-Day Fed Funds futures (ZQ) prices.

The logic, in brief:

- A ZQ contract settles at 100 minus the calendar-day average of the daily
  effective federal funds rate (EFFR) over the contract month, so
  ``implied average rate = 100 - price``.
- The realized EFFR published by the New York Fed pins down the pre-meeting
  rate ``r_pre`` (see ``pull_effr.py``); the published FedWatch tool
  anchors the same way.
- The meeting-month contract prices a day-weighted average of the pre- and
  post-meeting rates. If the meeting ends on day ``d`` of an ``N``-day month
  (the new rate takes effect the next day), then

      r_avg = (d/N) * r_pre + ((N-d)/N) * r_post

  which we solve for the expected post-meeting rate ``r_post``.
- Assuming the only possible outcomes are "no change" and a single 25 bp
  move, ``P(move) = |r_post - r_pre| / 0.25``.

All functions here are pure computations on DataFrames -- no network access.
``fedwatch_monitor.py`` assembles them into the forecast used by the
notebooks, the chart task, and the daily monitor.

HOMEWORK INSTRUCTIONS
---------------------
Three functions in this file have had their implementations removed:

- ``implied_rate``
- ``solve_post_meeting_rate``
- ``move_probability``

Each docstring specifies exactly what the function must do, and the notebook
``src/02_fedwatch_replication.ipynb.py`` derives the same formulas step by
step. Replace each ``raise NotImplementedError(...)`` body with your
implementation.

To verify your work (offline, no API key needed), run::

    pytest -vv ./src/test_fedwatch.py ./src/test_fedwatch_monitor.py
"""

import math
import re

import pandas as pd

from settings import config

MANUAL_DATA_DIR = config("MANUAL_DATA_DIR")

## CME futures month codes
MONTH_CODES = {
    "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
    "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
}  # fmt: skip

## An outright ZQ contract, e.g. "ZQU6". Calendar spreads look like "ZQU6-ZQZ6".
OUTRIGHT_RE = re.compile(r"^ZQ([FGHJKMNQUVXZ])(\d)$")


def load_fomc_meetings(data_dir=MANUAL_DATA_DIR):
    """Load the manually-maintained FOMC meeting calendar.

    See data_manual/data_README.md. The decision is announced on
    `meeting_end`; the new rate takes effect the following business day.
    """
    path = data_dir / "fomc_meetings.csv"
    meetings = pd.read_csv(path, parse_dates=["meeting_start", "meeting_end"])
    return meetings.sort_values("meeting_end").reset_index(drop=True)


def filter_outright_contracts(df):
    """Keep only outright monthly contracts (e.g. ZQU6), dropping calendar
    spreads (e.g. ZQU6-ZQZ6)."""
    return df[df["symbol"].str.match(OUTRIGHT_RE)]


def parse_zq_contract_month(symbol, reference_date):
    """Parse an outright ZQ symbol into its contract month.

    The single year digit is ambiguous (ZQU6 could be 2016 or 2026), so it is
    resolved to the unique year in [reference year - 1, reference year + 8]:
    ZQ lists only about three years of contracts, so any digit has exactly
    one plausible year near the reference date.

    >>> parse_zq_contract_month("ZQU6", pd.Timestamp("2026-08-06"))
    Period('2026-09', 'M')
    """
    m = OUTRIGHT_RE.match(symbol)
    if m is None:
        raise ValueError(f"Not an outright ZQ contract symbol: {symbol!r}")
    month = MONTH_CODES[m.group(1)]
    year_digit = int(m.group(2))
    ref_year = pd.Timestamp(reference_date).year
    for year in range(ref_year - 1, ref_year + 9):
        if year % 10 == year_digit:
            return pd.Period(year=year, month=month, freq="M")
    raise ValueError(f"Could not resolve year digit in {symbol!r}")  # unreachable


def implied_rate(price):
    """Average fed funds rate implied by a ZQ price: 100 - price.

    Works on scalars and pandas Series alike.
    """
    return 100 - price


def latest_prices_by_contract(df, as_of=None):
    """Latest available close per contract, as of a given date.

    ZQ months far from expiry trade thinly, so a contract may have no bar on
    the most recent trading day; using each contract's last available close
    on or before `as_of` handles those gaps. Spread symbols are dropped.

    Returns one row per contract with columns
    [symbol, contract_month, date, close], sorted by contract_month.
    """
    df = filter_outright_contracts(df)
    if as_of is None:
        as_of = df["date"].max()
    as_of = pd.Timestamp(as_of)
    df = df[df["date"] <= as_of]
    latest = (
        df.sort_values("date")
        .groupby("symbol", as_index=False)
        .last()[["symbol", "date", "close"]]
    )
    latest["contract_month"] = pd.PeriodIndex(
        [parse_zq_contract_month(s, as_of) for s in latest["symbol"]], freq="M"
    )
    return latest.sort_values("contract_month").reset_index(drop=True)[
        ["symbol", "contract_month", "date", "close"]
    ]


def solve_post_meeting_rate(r_avg, r_pre, meeting_end):
    """Solve the day-weighted average for the expected post-meeting rate.

    The meeting ends on day d of an N-day month and the new rate takes
    effect the next day, so d days accrue at r_pre and N - d at r_post:

        r_avg = (d/N) * r_pre + ((N-d)/N) * r_post

    Solve this equation for ``r_post`` and return it. (Hint: ``pd.Timestamp``
    has ``.day`` and ``.days_in_month`` attributes.)
    """
    meeting_end = pd.Timestamp(meeting_end)
    d = meeting_end.day
    n = meeting_end.days_in_month
    return (r_avg * n - r_pre * d) / (n - d)


def move_probability(r_pre, r_post, step=0.25):
    """Probability of a single `step`-sized move vs. no change.

    The binary-outcome model: the market prices either no change or exactly
    one move of `step` (25 bp), so the expected change identifies the
    probability: P(move) = |r_post - r_pre| / step, clipped to [0, 1].

    Returns a dict with exactly three keys:

    - ``"direction"``: ``"hike"`` if r_post > r_pre, ``"cut"`` if
      r_post < r_pre, else ``"no change"``
    - ``"p_move"``: the clipped probability defined above
    - ``"p_no_change"``: 1 - p_move
    """
    change = r_post - r_pre
    if change > 0:
        direction = "hike"
    elif change < 0:
        direction = "cut"
    else:
        direction = "no change"
    p_move = min(max(abs(change) / step, 0.0), 1.0)
    return {
        "direction": direction,
        "p_move": p_move,
        "p_no_change": 1 - p_move,
    }


def current_target_range(r_pre, step=0.25):
    """Infer the current target range from the pre-meeting implied rate.

    EFFR trades inside the Fed's 25 bp target range, so flooring the implied
    rate to the 25 bp grid recovers the range: 4.33 -> (4.25, 4.50).
    """
    lower = math.floor(r_pre / step) * step
    return (lower, lower + step)


def range_label(lower, step=0.25):
    """FedWatch-style label for a target range, in basis points: 4.25 -> '425-450'."""
    return f"{round(lower * 100)}-{round((lower + step) * 100)}"


def outcome_table(r_pre, probs_info):
    """Tabulate the binary-model outcomes as a FedWatch-style DataFrame.

    One row per possible outcome (columns: outcome, target_range,
    probability), in ascending rate order. The current target range is
    inferred by snapping ``r_pre`` to the 25 bp grid.
    """
    lower, _ = current_target_range(r_pre)
    outcomes = [
        {
            "lower": lower,
            "outcome": f"{range_label(lower)} (no change)",
            "target_range": range_label(lower),
            "probability": probs_info["p_no_change"],
        }
    ]
    if probs_info["direction"] == "cut":
        moved_lower = lower - 0.25
    elif probs_info["direction"] == "hike":
        moved_lower = lower + 0.25
    else:
        moved_lower = None
    if moved_lower is not None:
        outcomes.append(
            {
                "lower": moved_lower,
                "outcome": f"{range_label(moved_lower)} ({probs_info['direction']})",
                "target_range": range_label(moved_lower),
                "probability": probs_info["p_move"],
            }
        )
    return (
        pd.DataFrame(outcomes)
        .sort_values("lower")
        .drop(columns="lower")
        .reset_index(drop=True)
    )


