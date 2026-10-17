# Methodology

## Approach

A ZQ contract settles at 100 minus the calendar-day average EFFR over its
month, so `implied average rate = 100 − price`. Three steps turn that into
meeting probabilities:

1. **EFFR anchor.** The fed funds rate only moves when the FOMC moves it,
   so the latest realized EFFR print (published each morning by the New
   York Fed, pulled from FRED) is the pre-meeting rate `r_pre`. The
   published FedWatch tool anchors the same way.
2. **Day-weighted blend.** The meeting ends on day `d` of an `N`-day month
   and the new rate takes effect the next day, so
   `r_avg = (d/N)·r_pre + ((N−d)/N)·r_post`; solve for the expected
   post-meeting rate `r_post`.
3. **Binary outcome model.** If the only outcomes are "no change" and one
   25 bp move, `P(move) = |r_post − r_pre| / 0.25`, clipped to [0, 1]. The
   current target range is inferred by flooring `r_pre` to the 25 bp grid.

The full derivation, with a worked example, is in the notebook *Replicating
the CME FedWatch Tool*.

## Implementation Notes

- The math lives in `src/fedwatch.py` as pure functions;
  `src/fedwatch_monitor.py` assembles them into the forecast used by the
  chart task, the notebook, and the daily monitor (`doit monitor`). Both
  modules have hand-computed unit tests.
- Contract symbols are parsed with the CME month codes; the single year
  digit is resolved to the unique year near the data window.
- Thinly-traded months can miss daily bars, so each contract uses its last
  available close on or before the as-of date.
- When a meeting falls in the last ~3 days of a month, the solve is noisy
  (it divides by `N − d`), so the forecast reads the *next* month's
  contract directly instead, as FedWatch does.
- The forecast rolls to the following meeting on decision day itself, since
  that day's close already reflects the announcement.

## Caveats and Limitations

- For a day or two after each decision, the latest EFFR print predates the
  new target taking effect; those runs are flagged `anchor_stale` and
  should be treated as unreliable.
- Multi-meeting probability trees and moves larger than 25 bps are out of
  scope by design.
