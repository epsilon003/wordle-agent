# wordle-agent

An autonomous agent that solves the live NYT Wordle using an
entropy-maximizing solver, with an optional hosted pipeline that runs it
daily and tracks results on a dashboard.

**Status: working end-to-end**, both locally and in the hosted setup
(daily GitHub Actions run → Cloudflare Pages API → Supabase → dashboard).

## How it works

- **`solver.py`** — the actual intelligence. Opens with a fixed
  high-entropy word (`salet`), then for every subsequent guess computes
  the Shannon entropy each candidate guess would induce over the
  remaining possible answers, and picks the guess with max expected
  information gain (same idea as 3Blue1Brown's Wordle solver). Once the
  candidate set narrows to ≤10 words, it switches to guessing only from
  among those candidates, trading a sliver of long-run optimality for
  always taking a real shot at solving that turn instead of "wasting" a
  probe guess.
- **`player.py`** — Playwright browser automation for a local, visible
  run. Opens nytimes.com/games/wordle, dismisses the cookie banner, the
  "Play" click, the how-to-play modal, and any stray promo/ad popups
  , types each guess via keyboard events,
  reads the resulting tile colors from `div[data-testid="tile"]`
  , and feeds the feedback back into the solver until
  solved or 6 guesses are used.
- **`runner_headless.py`** — the same flow, headless, with no popup
  fighting UI to watch — meant for CI. After solving, POSTs the result
  (date, word, guesses, attempt count, duration) to a hosted ingest API.
- **`debug_dom.py`** — diagnostic script that dumps NYT's actual DOM
  structure (custom elements, shadow roots, tile-like elements) when
  something breaks. Useful if NYT changes their markup again.
- **`simulate.py`** — offline correctness/perf check, no browser needed.

## Quick local run

```bash
pip install -r requirements.txt
python -m playwright install chromium
python player.py
```

Runs with a visible browser window by default so you can watch it play
and debug if something looks off. `DELAY_BETWEEN_ATTEMPTS` and
`DELAY_AFTER_SUCCESS` at the top of `player.py` control the pacing if you
want more time to watch each guess land.

## Results (validated offline, no browser)

```bash
python simulate.py
```
Solver against 60 random real Wordle answers: **100% solved, average 3.6
guesses**, max 5.

## Hosted, autonomous version

`dashboard/` + `.github/workflows/daily-solve.yml` turn this into a fully
autonomous daily solver with a metrics dashboard:

```
GitHub Actions (daily cron, real VM)
  → runner_headless.py plays the day's Wordle
  → POSTs result to Cloudflare Pages Function (/api/runs)
  → written to Supabase Postgres
  → dashboard (Cloudflare Pages, Vite+React) reads it back and charts it
```

## Files

```
solver.py                                entropy solver + pattern logic
player.py                                live browser automation (local, visible)
runner_headless.py                       same, headless, posts results to the hosted API (CI)
debug_dom.py                             dumps NYT's real DOM structure for debugging
simulate.py                              offline solver validation harness
allowed_words.txt/ possible_words.txt    NYT's guess/answer dictionaries
requirements.txt

.github/workflows/daily-solve.yml        the daily cron

dashboard/                               Cloudflare Pages project
  src/                                   Vite+React dashboard UI
  functions/api/runs.ts                  ingest + read API (Pages Function)
  supabase/schema.sql                    run once in Supabase's SQL editor
  wrangler.toml
```
