"""Unit tests for the monitor path. All offline -- hand-computed fixtures only."""

import math
import warnings

import pandas as pd
import pytest

import fedwatch_monitor

MEETINGS = pd.DataFrame(
    {
        "meeting_start": pd.to_datetime(["2026-09-15", "2026-10-27", "2026-12-08"]),
        "meeting_end": pd.to_datetime(["2026-09-16", "2026-10-28", "2026-12-09"]),
    }
)


def make_futures(date, symbol_closes):
    return pd.DataFrame(
        {
            "date": pd.to_datetime([date] * len(symbol_closes)),
            "symbol": list(symbol_closes),
            "close": list(symbol_closes.values()),
        }
    )


def make_effr(date_values):
    return pd.DataFrame(
        {
            "date": pd.to_datetime(list(date_values)),
            "effr": list(date_values.values()),
        }
    )


def test_next_undecided_meeting_rolls_on_decision_day():
    # The day before the decision, the meeting is still undecided...
    assert fedwatch_monitor.next_undecided_meeting(
        MEETINGS, "2026-09-15"
    ) == pd.Timestamp("2026-09-16")
    # ...but on the decision day the close already reflects the outcome.
    assert fedwatch_monitor.next_undecided_meeting(
        MEETINGS, "2026-09-16"
    ) == pd.Timestamp("2026-10-28")
    with pytest.raises(ValueError, match="fomc_meetings.csv"):
        fedwatch_monitor.next_undecided_meeting(MEETINGS, "2026-12-09")


def test_latest_effr():
    effr = make_effr({"2026-08-04": 4.33, "2026-08-05": 4.34})
    date, rate = fedwatch_monitor.latest_effr(effr, "2026-08-05")
    assert date == pd.Timestamp("2026-08-05")
    assert rate == 4.34
    date, rate = fedwatch_monitor.latest_effr(effr, "2026-08-04")
    assert rate == 4.33
    with pytest.raises(ValueError, match="pull_effr"):
        fedwatch_monitor.latest_effr(effr, "2026-08-03")


def test_check_calendar_horizon():
    # Calendar ends 2026-12-09. Far out: no warning.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        fedwatch_monitor.check_calendar_horizon(MEETINGS, "2026-01-01")
    # Inside the warn window (< 180 days):
    with pytest.warns(UserWarning, match="fomc_meetings.csv"):
        fedwatch_monitor.check_calendar_horizon(MEETINGS, "2026-08-12")
    # Inside the error window (< 60 days):
    with pytest.raises(ValueError, match="fomc_meetings.csv"):
        fedwatch_monitor.check_calendar_horizon(MEETINGS, "2026-10-15")


def test_compute_monitor_forecast_effr_anchor():
    """EFFR anchor replaces the futures anchor in the same day-weighted solve.

    Meeting Sep 16, 2026 (d=16, N=30). The Sep contract is priced from a
    futures-implied path (r_pre 4.33, r_post 4.0925), but EFFR prints 4.32,
    so the solve runs with 4.32: r_post = (r_avg*30 - 4.32*16)/14.
    """
    r_avg = (16 * 4.33 + 14 * 4.0925) / 30
    futures = make_futures("2026-08-05", {"ZQU6": 100 - r_avg, "ZQQ6": 95.67})
    effr = make_effr({"2026-08-05": 4.32})

    summary, probs = fedwatch_monitor.compute_monitor_forecast(
        futures, effr, MEETINGS
    )

    assert summary["as_of"] == pd.Timestamp("2026-08-05")
    assert summary["meeting_end"] == pd.Timestamp("2026-09-16")
    assert summary["anchor_source"] == "EFFR"
    assert summary["anchor_stale"] is False
    assert summary["method"] == "day_weighted"
    assert summary["contract_symbol"] == "ZQU6"
    assert summary["r_pre"] == 4.32
    # (126.575 - 4.32*16) / 14
    assert summary["r_post"] == pytest.approx(4.1039286, abs=1e-6)
    assert summary["direction"] == "cut"
    assert summary["p_move"] == pytest.approx(0.8642857, abs=1e-6)
    assert list(probs["outcome"]) == ["400-425 (cut)", "425-450 (no change)"]
    assert probs["probability"].sum() == pytest.approx(1.0)


def test_monitor_rolls_and_flags_stale_anchor_after_decision():
    """The morning after a decision: roll to the next meeting, but the latest
    EFFR print (from the decision day) may not reflect the outcome yet."""
    futures = make_futures("2026-09-16", {"ZQV6": 95.75, "ZQU6": 95.78})
    effr = make_effr({"2026-09-16": 4.33})

    with pytest.warns(UserWarning, match="EFFR print"):
        summary, _ = fedwatch_monitor.compute_monitor_forecast(
            futures, effr, MEETINGS
        )
    assert summary["meeting_end"] == pd.Timestamp("2026-10-28")
    assert summary["anchor_stale"] is True

    # Once EFFR prints for a post-decision date, the anchor is fresh again.
    effr = make_effr({"2026-09-17": 4.08})
    futures = make_futures("2026-09-17", {"ZQV6": 95.75, "ZQU6": 95.78})
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        summary, _ = fedwatch_monitor.compute_monitor_forecast(
            futures, effr, MEETINGS
        )
    assert summary["anchor_stale"] is False
    assert summary["r_pre"] == 4.08


def test_month_end_rule_reads_next_month_contract():
    """A meeting on day 29 of a 30-day month: the next month's contract
    prices the post-meeting rate directly, no day-weighting."""
    meetings = pd.DataFrame(
        {
            "meeting_start": pd.to_datetime(["2026-09-28"]),
            "meeting_end": pd.to_datetime(["2026-09-29"]),
        }
    )
    r_post_true = 4.13
    futures = make_futures(
        "2026-08-05", {"ZQV6": 100 - r_post_true, "ZQU6": 95.78}
    )
    effr = make_effr({"2026-08-05": 4.33})

    summary, _ = fedwatch_monitor.compute_monitor_forecast(futures, effr, meetings)

    assert summary["method"] == "next_month_direct"
    assert summary["contract_symbol"] == "ZQV6"
    assert math.isnan(summary["r_avg"])
    assert summary["r_post"] == pytest.approx(r_post_true)
    assert summary["direction"] == "cut"
    assert summary["p_move"] == pytest.approx(0.8)


def test_append_history_dedups_on_as_of_and_meeting(tmp_path):
    path = tmp_path / "history.parquet"
    base = {
        "as_of": pd.Timestamp("2026-08-05"),
        "meeting_end": pd.Timestamp("2026-09-16"),
        "p_move": 0.95,
    }

    history = fedwatch_monitor.append_history(base, path=path)
    assert len(history) == 1

    day2 = {**base, "as_of": pd.Timestamp("2026-08-06"), "p_move": 0.90}
    history = fedwatch_monitor.append_history(day2, path=path)
    assert len(history) == 2

    # Re-running the same as-of date replaces the row instead of duplicating.
    rerun = {**day2, "p_move": 0.91}
    history = fedwatch_monitor.append_history(rerun, path=path)
    assert len(history) == 2
    assert history.iloc[-1]["p_move"] == 0.91
