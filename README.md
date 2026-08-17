# wordle-agent

Plays the live NYT Wordle automatically using an entropy-maximizing solver.

## How it works

- **`solver.py`** — the actual intelligence. Opens with a fixed high-entropy
  word (`salet`), then for every subsequent guess computes the Shannon
  entropy each candidate guess would induce over the remaining possible
  answers, and picks the guess with max expected information gain. This is
  the same idea as 3Blue1Brown's Wordle solver.
- **`player.py`** — Playwright browser automation. Opens nytimes.com/games/wordle,
  types each guess via keyboard events, reads the resulting tile colors back
  out of the DOM (piercing NYT's shadow-DOM web components), and feeds the
  feedback back into the solver until solved or 6 guesses are used.
- **`simulate.py`** — offline correctness/perf check, no browser needed.

## Results (validated in this sandbox, offline)

Ran the solver against 60 random real Wordle answers with no browser
involved: **100% solved, average 3.6 guesses**, max 5. See `simulate.py`.

## Autonomous daily runs + dashboard

**Manual autonomous run:**
```bash
python player.py --headless --no-login   # plays today's puzzle, no browser window, logs to stats.json
python dashboard.py --open               # regenerates dashboard.html and opens it
```

**Fully scheduled (Windows):** run once, from an elevated PowerShell prompt
inside this folder:
```powershell
.\setup_scheduler.ps1
```
This registers a Windows Scheduled Task that runs both commands above
every day at a time you pick. Re-running the puzzle on a day it's already
logged is a safe no-op (`player.py` checks `stats.json` first). Undo with:
```powershell
Unregister-ScheduledTask -TaskName "WordleAgent" -Confirm:$false
```

**Stats + dashboard:**
- `stats_store.py` appends one record per day to `stats.json` (word, guesses,
  solved/failed, elapsed time).
- `dashboard.py` reads `stats.json` and writes a self-contained
  `dashboard.html` (win rate, streak, guess-distribution chart, guesses-
  over-time chart, recent games table). It loads Chart.js from a CDN, so it
  needs internet the moment you open it, but otherwise works fully offline.
- If today's puzzle was already completed outside this script (e.g. you
  played it by hand), `player.py` detects the filled board, logs what it
  can see, and skips playing rather than fighting with an already-finished
  game.



By default the game plays anonymously - nothing is saved to any account.
If you want your streak/stats to persist on nytimes.com itself, `player.py`
uses a **persistent browser profile** (`.browser_profile/`, created next to
the script) rather than ever touching your Google password directly:

1. Run `python player.py` with `require_login=True` (the default).
2. The first time, it'll pause and ask you to click "Log in" -> "Continue
   with Google" in the opened browser window and finish sign-in yourself.
3. That session is saved to disk. Every future run reuses it automatically
   — no login step, no credentials ever stored in the script.

`.browser_profile/` contains real session cookies, so treat it like a
password: don't commit it to git or share it. Add it to `.gitignore` if
this becomes a repo.



```bash
pip install playwright
playwright install chromium
python player.py
```

⚠️ **Important**: I built and tested `solver.py` end-to-end (see
`simulate.py`'s output), but I could **not** test `player.py` against the
live NYT site — this sandbox's network egress is domain-allowlisted and
`nytimes.com` isn't reachable from it. The DOM-reading logic
(`DEEP_QUERY_TILES_JS`) is written defensively (recursively pierces all
shadow roots looking for `[data-state]` tiles rather than hardcoding brittle
class names), but if NYT has changed their markup you may need to tweak:
- the `game-tile` tag name check in `DEEP_QUERY_TILES_JS`
- the modal-dismissal selectors in `dismiss_modals()`

Run with `headless=False` (default) the first time so you can watch it and
debug visually if a selector needs adjusting.

## Files
- `solver.py` — entropy solver + pattern logic
- `player.py` — live browser automation
- `simulate.py` — offline validation harness
- `allowed_words.txt` / `possible_words.txt` — NYT's guess/answer dictionaries
