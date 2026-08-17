"""
Headless, CI-friendly version of player.py. No login, no persistent
profile (each GitHub Actions run is a fresh VM anyway) - just plays the
day's word and POSTs the result to the dashboard's ingest API.

Env vars required:
    WORDLE_API_URL   e.g. https://your-app.vercel.app/api/runs
    INGEST_SECRET    must match INGEST_SECRET set in your Vercel project

Usage (see .github/workflows/daily-solve.yml for the scheduled version):
    python runner_headless.py
"""
import os
import sys
import time
import datetime as dt
import urllib.request
import json as jsonlib

from playwright.sync_api import sync_playwright

from solver import WordleSolver
from player import (
    WORDLE_URL, TILE_SELECTOR,
    dismiss_cookie_banner, dismiss_stray_popups, start_game, type_guess,
    clear_current_row, read_all_tile_states, is_invalid_word_toast, best_fallback,
)


def post_result(payload: dict):
    api_url = os.environ.get("WORDLE_API_URL")
    secret = os.environ.get("INGEST_SECRET")
    if not api_url or not secret:
        print("WORDLE_API_URL / INGEST_SECRET not set - skipping POST, printing result instead:")
        print(jsonlib.dumps(payload, indent=2))
        return

    data = jsonlib.dumps(payload).encode()
    req = urllib.request.Request(
        api_url, data=data, method="POST",
        headers={
            "Content-Type": "application/json",
            "x-ingest-secret": secret,
            # Default urllib UA ("Python-urllib/3.x") gets flagged by
            # Cloudflare's Bot Fight Mode / WAF and blocked with a 403
            # before the request ever reaches the Pages Function. A normal
            # UA is usually enough to get past that layer.
            "User-Agent": "Mozilla/5.0 (compatible; wordle-agent-runner/1.0)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"POST {api_url} -> {resp.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"POST {api_url} -> {e.code} {e.reason}\nResponse body: {body}")
        raise


def run():
    start_time = time.time()
    solver = WordleSolver()
    tried_words = set()
    guess_log = []
    solved = False
    final_word = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(WORDLE_URL, timeout=30000)
        time.sleep(1.5)

        dismiss_cookie_banner(page)
        start_game(page)

        try:
            page.wait_for_selector(TILE_SELECTOR, timeout=8000)
        except Exception:
            print("Board didn't appear yet; retrying popup dismissal...")
            dismiss_stray_popups(page)
            start_game(page)
            try:
                page.wait_for_selector(TILE_SELECTOR, timeout=10000)
            except Exception:
                page.screenshot(path="ci_debug_board_not_loaded.png")
                print(
                    "ERROR: game board never appeared after two attempts. "
                    "Saved ci_debug_board_not_loaded.png."
                )
                browser.close()
                sys.exit(1)

        time.sleep(0.5)

        for attempt in range(1, 7):
            guess = solver.next_guess()
            while guess in tried_words:
                guess = best_fallback(solver, tried_words)
            tried_words.add(guess)

            type_guess(page, guess)
            time.sleep(2.3)

            if is_invalid_word_toast(page):
                clear_current_row(page)
                solver.guess_count -= 1
                guess2 = best_fallback(solver, tried_words)
                type_guess(page, guess2)
                time.sleep(2.3)
                guess = guess2
                tried_words.add(guess)

            states = read_all_tile_states(page)
            row = states[(attempt - 1) * 5: attempt * 5]

            if any(s in (None, "empty", "tbd") for s in row):
                page.screenshot(path=f"ci_debug_attempt_{attempt}.png")
                print(f"Row {attempt} didn't resolve: {row}")
                break

            state_map = {"correct": 2, "present": 1, "absent": 0}
            pattern = [state_map[s] for s in row]
            guess_log.append({"guess": guess, "pattern": pattern})

            if solver.is_solved(pattern):
                solved = True
                final_word = guess
                break

            solver.update(guess, pattern)
            if not solver.candidates:
                break

        browser.close()

    payload = {
        "puzzle_date": dt.date.today().isoformat(),
        "word": final_word,
        "guesses": guess_log,
        "num_attempts": len(guess_log),
        "solved": solved,
        "duration_seconds": round(time.time() - start_time, 1),
    }
    print(payload)
    post_result(payload)


if __name__ == "__main__":
    run()