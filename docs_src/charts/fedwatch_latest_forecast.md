# FedWatch: Next FOMC Meeting Probabilities

Probability of each fed funds target-range outcome at the next scheduled FOMC
meeting, implied by 30-Day Fed Funds futures (ZQ) prices. This replicates the
simplest case of the
[CME FedWatch tool](https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html).

**Method.** A ZQ contract settles at 100 minus the calendar-day average EFFR
over its month. The latest realized EFFR print (published by the New York
Fed) pins the pre-meeting rate r_pre — the same anchor the published tool
uses. The meeting-month contract prices a day-weighted average,
r_avg = (d/N)·r_pre + ((N−d)/N)·r_post, where the meeting ends on day d of an
N-day month; solving gives the expected post-meeting rate r_post. Assuming
the only outcomes are "no change" and a single 25 bp move,
P(move) = |r_post − r_pre| / 0.25.

**Caveats.** When the meeting falls in the last few days of a month, the
next month's contract is read directly instead (as FedWatch does); for a day
or two after each decision the EFFR anchor may not yet reflect the new
target; multi-meeting probability trees and moves larger than 25 bps are out
of scope. See the notebook *Replicating the CME FedWatch Tool* for the full
derivation.
