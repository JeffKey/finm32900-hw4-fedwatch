[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/ATHvtNp-)
# HW 4: A Daily FedWatch Monitor

This homework turns the in-class FedWatch case study into a live monitor. The
pipeline pulls 30-Day Fed Funds futures (ZQ) from Databento and the effective
federal funds rate (EFFR) from FRED, computes the market-implied probability of
a hike, cut, or no change at the next FOMC meeting, and renders the forecast
chart into a chartbook site. You will (1) fill in the small amount of math that
has been removed and (2) publish the site so that a GitHub Action rebuilds it
every morning, unattended.

Run `pytest` and make the tests pass. 3 points total.

Notes before you start:

- `pytest -vv ./src/test_fedwatch.py ./src/test_fedwatch_monitor.py` runs
  offline with no API key — use it as your feedback loop for Task 1. Expect 6
  failures until Task 1 is done.
- Plain `doit` (the full pipeline) will not succeed until Task 1 is complete
  (the chart and both notebooks call the stubbed functions), and it needs your
  Databento API key in `.env`.

## Tasks

### Task 1: Fill in the FedWatch math (1 pt)

Three functions in `src/fedwatch.py` have had their bodies replaced with
`raise NotImplementedError(...)`:

- `implied_rate`
- `solve_post_meeting_rate`
- `move_probability`

Each docstring specifies exactly what the function must do, and the notebook
`src/02_fedwatch_replication.ipynb.py` derives the same formulas step by step.

Graded by:

```bash
pytest -vv ./src/test_fedwatch.py ./src/test_fedwatch_monitor.py
```

Then run the full pipeline locally: copy `.env.example` to `.env`, add your
Databento API key (databento.com → Account → API keys; the pull is
cost-guarded and free), and run `doit`. The built site lands in
`docs/index.html`.

### Task 2: Stand up your daily self-updating site (2 pts)

The workflow in `.github/workflows/deploy_pages.yml` rebuilds the pipeline and
publishes the chartbook site to GitHub Pages — on every push to `main` and on
a daily cron (14:30 UTC, mid-morning Chicago, after the NY Fed's ~9 AM ET EFFR
print). It is gated to do nothing inside the course org, so you will run it
from a repo of your own:

1. Create a new **public** repo under your **personal** GitHub account, e.g.
   `finm32900-hw4-fedwatch`. Do **not** make this assignment repo public, and
   do not enable Pages on it.

2. Push your completed pipeline there:

   ```bash
   git remote add public https://github.com/<you>/finm32900-hw4-fedwatch.git
   git push public main
   ```

   Never commit `.env` — in CI the workflow reads the key from a repository
   secret instead.

3. On the public repo, add the secret: Settings → Secrets and variables →
   Actions → New repository secret → name `DATABENTO_API_KEY`. Or:

   ```bash
   gh secret set DATABENTO_API_KEY --repo <you>/finm32900-hw4-fedwatch
   ```

4. Run it once by hand: Actions tab → "Build and Deploy FedWatch Site" → Run
   workflow. Wait for green — the run pulls the data, executes the notebooks,
   renders the forecast chart, builds the chartbook site, runs the tests, and
   force-pushes the built site to the `gh-pages` branch.

5. Enable Pages: Settings → Pages → Deploy from a branch → `gh-pages` /
   `/ (root)`. Confirm the site is live at
   `https://<you>.github.io/finm32900-hw4-fedwatch/` and shows the
   "FedWatch: Next FOMC Meeting Probabilities" chart.

6. That's the monitor: the cron now refreshes the forecast every morning with
   no action from you. (GitHub pauses cron schedules after ~60 days without
   repo activity; the Actions tab shows a re-enable button if that happens.)

7. Back in **this** repo, open `src/monitor_self_attestation.py`, set the flag
   to `True`, paste your live site URL, then commit and push.

Graded by:

```bash
pytest -vv ./src/test_monitor_self_attestation.py
```

I will visit the URL you provide and check that the site is live and current.

## Warnings

- This assignment repo must stay **private** — it is your graded work. Your
  separate deploy repo will be public, including your completed Task 1 code;
  that is intended for this assignment.
- Your API key goes into `.env` locally and into the Actions secret in CI. If
  it ends up in a commit anywhere, revoke it and generate a new one.
- Do not edit the test files (`test_*.py`). If you do, you will be required to
  remove those changes from your Git history.

## Setup

```bash
conda create -n finm python=3.12
conda activate finm
pip install -r requirements.txt
cp .env.example .env   # then add your DATABENTO_API_KEY
doit
```
