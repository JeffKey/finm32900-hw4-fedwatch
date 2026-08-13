"""Render the latest FedWatch-style forecast chart.

Produces the probability bar chart for the next FOMC meeting in two formats:

- ``_output/fedwatch_latest_forecast.png`` (matplotlib, for static reports)
- ``_output/fedwatch_latest_forecast.html`` (plotly, for the chartbook site)

All computation lives in ``fedwatch`` / ``fedwatch_monitor`` (EFFR-anchored,
like the published tool); this module only renders.
"""

import matplotlib.pyplot as plt
import plotly.graph_objects as go

import fedwatch
import fedwatch_monitor
import pull_effr
import pull_fed_funds_futures
from settings import config

OUTPUT_DIR = config("OUTPUT_DIR")

BAR_COLOR = "#1f77b4"
INK_MUTED = "#595959"


def _titles(summary):
    title = (
        f"Target rate probabilities for the "
        f"{summary['meeting_end']:%b %d, %Y} FOMC meeting"
    )
    subtitle = (
        f"Implied by 30-Day Fed Funds futures (ZQ), "
        f"as of {summary['as_of']:%Y-%m-%d}"
    )
    return title, subtitle


def _tick_labels(probs):
    # "350-375 (no change)" -> "350-375\n(no change)", plus a bps hint
    return [
        outcome.replace(" (", "\n(") for outcome in probs["outcome"]
    ]


def plot_probabilities_matplotlib(summary, probs, ax=None):
    """FedWatch-style bar chart of next-meeting outcome probabilities."""
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4.5))
    title, subtitle = _titles(summary)

    pct = probs["probability"] * 100
    bars = ax.bar(_tick_labels(probs), pct, color=BAR_COLOR, width=0.5)
    ax.bar_label(bars, fmt="%.1f%%", padding=3)

    ax.set_ylim(0, 100)
    ax.set_ylabel("Probability (%)")
    ax.set_xlabel("Target range (bps)")
    ax.yaxis.grid(True, color="0.9")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(subtitle, fontsize=9, color=INK_MUTED)
    ax.figure.suptitle(title, fontsize=12, fontweight="bold")
    ax.figure.tight_layout()
    return ax


def plot_probabilities_plotly(summary, probs):
    """The same chart as an interactive plotly figure (for the chartbook site)."""
    title, subtitle = _titles(summary)
    pct = probs["probability"] * 100
    fig = go.Figure(
        go.Bar(
            x=[label.replace("\n", "<br>") for label in _tick_labels(probs)],
            y=pct,
            marker_color=BAR_COLOR,
            text=[f"{p:.1f}%" for p in pct],
            textposition="outside",
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        template="simple_white",
        title=dict(text=f"{title}<br><sup>{subtitle}</sup>"),
        yaxis=dict(title="Probability (%)", range=[0, 100]),
        xaxis=dict(title="Target range (bps)"),
    )
    return fig


if __name__ == "__main__":
    df = pull_fed_funds_futures.load_fed_funds_futures()
    effr = pull_effr.load_effr()
    meetings = fedwatch.load_fomc_meetings()
    summary, probs = fedwatch_monitor.compute_monitor_forecast(df, effr, meetings)

    for key, value in summary.items():
        print(f"{key}: {value}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ax = plot_probabilities_matplotlib(summary, probs)
    ax.figure.savefig(
        OUTPUT_DIR / "fedwatch_latest_forecast.png", dpi=300, bbox_inches="tight"
    )

    fig = plot_probabilities_plotly(summary, probs)
    fig.write_html(
        OUTPUT_DIR / "fedwatch_latest_forecast.html", include_plotlyjs="cdn"
    )
    print(f"Wrote charts to {OUTPUT_DIR}")
