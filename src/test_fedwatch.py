"""Unit tests for the FedWatch math. All offline -- hand-computed fixtures only."""

import pandas as pd
import pytest

import fedwatch

AS_OF = pd.Timestamp("2026-08-06")


def test_parse_zq_contract_month():
    assert fedwatch.parse_zq_contract_month("ZQU6", AS_OF) == pd.Period("2026-09")
    assert fedwatch.parse_zq_contract_month(
        "ZQZ5", pd.Timestamp("2026-02-01")
    ) == pd.Period("2025-12")
    assert fedwatch.parse_zq_contract_month("ZQF7", AS_OF) == pd.Period("2027-01")


def test_parse_zq_contract_month_rejects_non_outrights():
    with pytest.raises(ValueError):
        fedwatch.parse_zq_contract_month("ZQU6-ZQZ6", AS_OF)
    with pytest.raises(ValueError):
        fedwatch.parse_zq_contract_month("ESU6", AS_OF)


def test_filter_outright_contracts():
    df = pd.DataFrame({"symbol": ["ZQQ6", "ZQU6-ZQZ6", "ZQZ6"], "close": [1, 2, 3]})
    out = fedwatch.filter_outright_contracts(df)
    assert list(out["symbol"]) == ["ZQQ6", "ZQZ6"]


def test_implied_rate():
    assert fedwatch.implied_rate(95.6725) == pytest.approx(4.3275)
    series = pd.Series([95.0, 96.0])
    assert list(fedwatch.implied_rate(series)) == [5.0, 4.0]


def test_solve_post_meeting_rate_round_trip():
    # Meeting ends Sep 16, 2026: N=30 days, d=16 pre-meeting days.
    r_pre, r_post_true = 4.33, 4.08
    r_avg = (16 * r_pre + 14 * r_post_true) / 30
    r_post = fedwatch.solve_post_meeting_rate(
        r_avg, r_pre, pd.Timestamp("2026-09-16")
    )
    assert r_post == pytest.approx(r_post_true)


def test_move_probability():
    result = fedwatch.move_probability(4.33, 4.0925)
    assert result["direction"] == "cut"
    assert result["p_move"] == pytest.approx(0.95)
    assert result["p_no_change"] == pytest.approx(0.05)

    hike = fedwatch.move_probability(4.33, 4.38)
    assert hike["direction"] == "hike"
    assert hike["p_move"] == pytest.approx(0.20)

    # A gap bigger than one step clips to probability 1
    clipped = fedwatch.move_probability(4.33, 4.03)
    assert clipped["p_move"] == 1.0


def test_current_target_range_and_label():
    assert fedwatch.current_target_range(4.33) == (4.25, 4.50)
    assert fedwatch.range_label(4.25) == "425-450"
    assert fedwatch.range_label(4.00) == "400-425"


def test_outcome_table():
    probs = fedwatch.outcome_table(
        4.33, {"direction": "cut", "p_move": 0.95, "p_no_change": 0.05}
    )
    assert list(probs["outcome"]) == ["400-425 (cut)", "425-450 (no change)"]
    assert list(probs["probability"]) == [0.95, 0.05]

    # "no change" direction yields a single row
    flat = fedwatch.outcome_table(
        4.33, {"direction": "no change", "p_move": 0.0, "p_no_change": 1.0}
    )
    assert list(flat["outcome"]) == ["425-450 (no change)"]


def test_load_fomc_meetings():
    meetings = fedwatch.load_fomc_meetings()
    assert list(meetings.columns) == ["meeting_start", "meeting_end"]
    assert pd.Timestamp("2026-09-16") in set(meetings["meeting_end"])


def make_synthetic_futures():
    """ZQQ6 (Aug 2026) and ZQU6 (Sep 2026), plus a calendar spread and a
    stale earlier bar that must both be ignored."""
    r_pre, r_post = 4.33, 4.0925
    r_avg = (16 * r_pre + 14 * r_post) / 30
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2026-08-04", "2026-08-05", "2026-08-05", "2026-08-05"]
            ),
            "symbol": ["ZQQ6", "ZQQ6", "ZQU6", "ZQU6-ZQZ6"],
            "close": [95.20, 100 - r_pre, 100 - r_avg, 0.105],
        }
    )


def test_latest_prices_by_contract():
    latest = fedwatch.latest_prices_by_contract(make_synthetic_futures())
    assert list(latest["symbol"]) == ["ZQQ6", "ZQU6"]  # sorted by contract month
    # The stale 08-04 bar is superseded by the 08-05 close
    assert latest.set_index("symbol").loc["ZQQ6", "close"] == pytest.approx(95.67)
    assert list(latest["contract_month"]) == [
        pd.Period("2026-08"),
        pd.Period("2026-09"),
    ]
