"""The FedWatch forecast, assembled for unattended daily runs.

``compute_monitor_forecast`` is the one forecast in this project: the
EFFR-anchored computation that notebook 02 derives step by step, with the
edge cases handled rather than warned about. The chart task renders it, and
the daily monitor (``doit monitor``) records it. The pieces:

- **EFFR anchor.** The pre-meeting rate is the latest realized EFFR print
  (via ``pull_effr``), as the published FedWatch tool does. Realized EFFR
  carries no market noise -- and noise in the anchor moves the probability
  by the same amplified factor as noise in the meeting-month contract.
- **Edge cases handled.** The forecast rolls to the next meeting the
  morning after a decision, and when a meeting falls in the last ~3 days of
  a month it reads the *next* month's contract directly (the whole next
  month accrues at the post-meeting rate), as FedWatch does, instead of
  dividing by a tiny number of post-meeting days.
- **It keeps history.** Each ``doit monitor`` run appends its snapshot to
  ``_data/fedwatch_history.parquet`` (one row per as-of date and meeting,
  re-runs replace), which is what makes a monitor: the probability *path*
  over time, not just today's bars.

Known limitation (documented, not yet handled): for a day or two after each
decision, the latest EFFR print predates the new target taking effect, so
the anchor may be off by the size of the move. The monitor detects this,
warns, and flags the snapshot with ``anchor_stale=True``; treat those rows
as unreliable. The proper fix is chaining the just-decided meeting's implied
outcome forward (the probability-tree extension).

Run the daily update with::

    doit monitor
"""

import warnings
from pathlib import Path

import pandas as pd

import fedwatch
from settings import config

DATA_DIR = config("DATA_DIR")
OUTPUT_DIR = config("OUTPUT_DIR")

HISTORY_PARQUET_NAME = "fedwatch_history.parquet"

## Fail/warn when the hand-maintained FOMC calendar is close to running out.
## The Fed publishes meeting dates years ahead, so a short horizon means
## data_manual/fomc_meetings.csv needs appending, not that meetings stopped.
CALENDAR_ERROR_DAYS = 60
CALENDAR_WARN_DAYS = 180


def next_undecided_meeting(meetings, as_of):
    """The first meeting whose outcome is still unknown at the `as_of` close.

    Strict inequality: on the decision day itself the closing price already
    reflects the announcement (made ~2pm ET), so the monitor rolls to the
    following meeting. Compare ``fedwatch.next_fomc_meeting``, which keeps a
    meeting through its decision day for teaching purposes.
    """
    as_of = pd.Timestamp(as_of)
    upcoming = meetings[meetings["meeting_end"] > as_of]
    if upcoming.empty:
        raise ValueError(
            f"No FOMC meeting after {as_of.date()} in the calendar. "
            "Update data_manual/fomc_meetings.csv."
        )
    return upcoming["meeting_end"].iloc[0]


def latest_effr(df_effr, as_of):
    """The most recent EFFR print on or before `as_of`: (date, rate)."""
    as_of = pd.Timestamp(as_of)
    available = df_effr[df_effr["date"] <= as_of]
    if available.empty:
        raise ValueError(
            f"No EFFR observation on or before {as_of.date()}. "
            "Re-pull with `python ./src/pull_effr.py`."
        )
    row = available.sort_values("date").iloc[-1]
    return row["date"], float(row["effr"])


def check_calendar_horizon(meetings, as_of):
    """Fail loudly as the hand-maintained FOMC calendar nears exhaustion."""
    as_of = pd.Timestamp(as_of)
    horizon = (meetings["meeting_end"].max() - as_of).days
    message = (
        f"The FOMC calendar ends {horizon} days after {as_of.date()}. "
        "Append the newly published meeting dates to "
        "data_manual/fomc_meetings.csv (see "
        "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm)."
    )
    if horizon < CALENDAR_ERROR_DAYS:
        raise ValueError(message)
    if horizon < CALENDAR_WARN_DAYS:
        warnings.warn(message, stacklevel=2)


def compute_monitor_forecast(df_futures, df_effr, meetings, as_of=None):
    """The FedWatch forecast for the next undecided meeting, EFFR-anchored.

    Parameters
    ----------
    df_futures : DataFrame from ``pull_fed_funds_futures.load_fed_funds_futures``.
    df_effr : DataFrame from ``pull_effr.load_effr`` (columns [date, effr]).
    meetings : DataFrame from ``fedwatch.load_fomc_meetings``.
    as_of : optional date; defaults to the latest date in the futures data.

    Returns
    -------
    (summary, probs) : summary is a flat dict of inputs, solved rates, and
    flags (one history row); probs is the outcome DataFrame, as in
    ``fedwatch.compute_fedwatch_forecast``.
    """
    latest = fedwatch.latest_prices_by_contract(df_futures, as_of=as_of)
    if as_of is None:
        as_of = latest["date"].max()
    as_of = pd.Timestamp(as_of)

    meeting_end = next_undecided_meeting(meetings, as_of)
    meeting_month = pd.Period(meeting_end, freq="M")

    effr_date, r_pre = latest_effr(df_effr, as_of)

    ## A decision announced on or after the latest EFFR print may have
    ## changed the target, and the print would not show it yet.
    decided = meetings["meeting_end"] <= as_of
    anchor_stale = bool((decided & (meetings["meeting_end"] >= effr_date)).any())
    if anchor_stale:
        warnings.warn(
            f"The latest EFFR print ({effr_date.date()}) predates the most "
            "recent FOMC decision taking effect, so the anchor may not "
            "reflect a rate change yet. This snapshot is flagged "
            "anchor_stale=True; expect it to be unreliable for a day or two "
            "after each meeting.",
            stacklevel=2,
        )

    ## Which contract to read. A meeting in the last ~3 days of its month
    ## leaves too few post-meeting days to divide by, so read the next
    ## month's contract instead: that whole month accrues at the
    ## post-meeting rate (to within a possible day or two of carryover at
    ## the start -- the same approximation FedWatch makes).
    near_month_end = meeting_end.day >= meeting_end.days_in_month - 2
    read_month = meeting_month + 1 if near_month_end else meeting_month

    by_month = latest.set_index("contract_month")
    if read_month not in by_month.index:
        raise ValueError(
            f"No ZQ contract for month {read_month} in the futures data. "
            "Re-pull with a wider window (doit forget pull && doit)."
        )
    contract = by_month.loc[read_month]

    if near_month_end:
        if meetings["meeting_end"].dt.to_period("M").eq(read_month).any():
            warnings.warn(
                f"The next-month contract {contract['symbol']} covers a month "
                "that itself contains an FOMC meeting, so it prices a blend; "
                "the forecast is a rougher approximation.",
                stacklevel=2,
            )
        method = "next_month_direct"
        r_avg = float("nan")
        r_post = fedwatch.implied_rate(contract["close"])
    else:
        method = "day_weighted"
        r_avg = fedwatch.implied_rate(contract["close"])
        r_post = fedwatch.solve_post_meeting_rate(r_avg, r_pre, meeting_end)

    probs_info = fedwatch.move_probability(r_pre, r_post)
    probs = fedwatch.outcome_table(r_pre, probs_info)

    summary = {
        "as_of": as_of,
        "meeting_end": meeting_end,
        "anchor_source": "EFFR",
        "effr_date": effr_date,
        "anchor_stale": anchor_stale,
        "contract_symbol": contract["symbol"],
        "contract_close": float(contract["close"]),
        "method": method,
        "r_pre": r_pre,
        "r_avg": r_avg,
        "r_post": r_post,
        **probs_info,
    }
    return summary, probs


def append_history(summary, path=None):
    """Append one snapshot row to the monitor history parquet.

    Keyed by (as_of, meeting_end): re-running the monitor for the same
    as-of date replaces that day's row instead of duplicating it. Returns
    the full updated history.
    """
    if path is None:
        path = DATA_DIR / HISTORY_PARQUET_NAME
    path = Path(path)
    history = pd.DataFrame([summary])
    if path.exists():
        history = pd.concat([pd.read_parquet(path), history], ignore_index=True)
    history = (
        history.drop_duplicates(subset=["as_of", "meeting_end"], keep="last")
        .sort_values(["as_of", "meeting_end"])
        .reset_index(drop=True)
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    history.to_parquet(path)
    return history


if __name__ == "__main__":
    import pull_effr
    import pull_fed_funds_futures

    df_futures = pull_fed_funds_futures.load_fed_funds_futures()
    df_effr = pull_effr.load_effr()
    meetings = fedwatch.load_fomc_meetings()

    summary, probs = compute_monitor_forecast(df_futures, df_effr, meetings)
    check_calendar_horizon(meetings, summary["as_of"])

    for key, value in summary.items():
        print(f"{key}: {value}")

    history = append_history(summary)
    print(f"History: {len(history)} snapshot(s) in {DATA_DIR / HISTORY_PARQUET_NAME}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    latest_csv = probs.copy()
    for key in ["as_of", "meeting_end", "r_pre", "r_post", "direction", "anchor_stale"]:
        latest_csv[key] = summary[key]
    latest_csv.to_csv(OUTPUT_DIR / "fedwatch_monitor_latest.csv", index=False)
    print(f"Wrote {OUTPUT_DIR / 'fedwatch_monitor_latest.csv'}")
    ## The charts themselves are rendered by fedwatch_chart.py, which the
    ## monitor task runs right after this script.
