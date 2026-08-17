"""
Automates playing the live NYT Wordle using the entropy solver.

DOM structure confirmed via debug_dom.py against the real site (Aug 2026):
plain React, no shadow DOM. Tiles are:
    <div data-testid="tile" data-state="empty|tbd|absent|present|correct"
         aria-label="Nth letter, ..." role="img">
in simple DOM order (30 tiles total, 6 rows x 5, grouped consecutively).

"""
import re
import time
from playwright.sync_api import sync_playwright, Page

from solver import WordleSolver, best_guess

WORDLE_URL = "https://www.nytimes.com/games/wordle/index.html"
TILE_SELECTOR = 'div[data-testid="tile"]'


def dismiss_cookie_banner(page: Page):
    for name in ["Accept all", "Reject all"]:
        try:
            btn = page.get_by_role("button", name=name)
            if btn.is_visible(timeout=2000):
                btn.click()
                time.sleep(0.3)
                return
        except Exception:
            pass


def start_game(page: Page):
    """Click Play, then close the how-to-play modal if it appears."""
    try:
        page.get_by_role("button", name="Play", exact=True).click(timeout=5000)
    except Exception:
        pass  # maybe already past the landing screen
    time.sleep(1)

    # "How to play" instructions modal - close it
    for sel in ['button[aria-label="Close"]', 'button[aria-label="Close dialog"]']:
        try:
            page.locator(sel).first.click(timeout=1500)
            time.sleep(0.3)
            return
        except Exception:
            pass
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass


def type_guess(page: Page, word: str):
    for ch in word:
        page.keyboard.press(ch.upper())
        time.sleep(0.08)
    page.keyboard.press("Enter")


def clear_current_row(page: Page):
    for _ in range(5):
        page.keyboard.press("Backspace")
        time.sleep(0.05)


def read_all_tile_states(page: Page):
    """Returns a flat list of data-state values for all 30 tiles, in DOM order."""
    return page.locator(TILE_SELECTOR).evaluate_all(
        "els => els.map(el => el.getAttribute('data-state'))"
    )


def is_invalid_word_toast(page: Page) -> bool:
    try:
        return page.get_by_text(re.compile("not in word list", re.I)).is_visible(timeout=800)
    except Exception:
        return False


def best_fallback(solver: WordleSolver, tried_words: set) -> str:
    """Pick the next-best guess that hasn't already been tried/rejected."""
    pool = [w for w in solver.allowed if w not in tried_words]
    return best_guess(solver.candidates, pool)


def play(headless: bool = False):
    solver = WordleSolver()
    tried_words = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(WORDLE_URL, timeout=30000)
        time.sleep(1.5)

        dismiss_cookie_banner(page)
        start_game(page)

        page.wait_for_selector(TILE_SELECTOR, timeout=10000)
        time.sleep(0.5)

        for attempt in range(1, 7):
            guess = solver.next_guess()
            while guess in tried_words:
                guess = best_fallback(solver, tried_words)
            tried_words.add(guess)

            print(f"Attempt {attempt}: guessing '{guess}'")
            type_guess(page, guess)
            time.sleep(2.3)  # let flip animations resolve

            if is_invalid_word_toast(page):
                print(f"  '{guess}' rejected by NYT as not in their word list; clearing and retrying.")
                clear_current_row(page)
                solver.guess_count -= 1  # this attempt didn't actually count
                guess2 = best_fallback(solver, tried_words)
                print(f"  retrying with '{guess2}'")
                type_guess(page, guess2)
                time.sleep(2.3)
                guess = guess2
                tried_words.add(guess)

            states = read_all_tile_states(page)
            row = states[(attempt - 1) * 5: attempt * 5]

            if any(s in (None, "empty", "tbd") for s in row):
                page.screenshot(path=f"debug_attempt_{attempt}_unresolved.png")
                print(f"  ERROR: row {attempt} didn't fully resolve: {row}. "
                      f"Saved debug_attempt_{attempt}_unresolved.png")
                break

            state_map = {"correct": 2, "present": 1, "absent": 0}
            pattern = tuple(state_map[s] for s in row)
            print(f"  feedback: {pattern}")

            if solver.is_solved(pattern):
                print(f"Solved in {attempt} guesses! Word was '{guess}'.")
                break

            solver.update(guess, pattern)
            if not solver.candidates:
                print("  No candidates left - word list mismatch with NYT's dictionary.")
                break
        else:
            print("Did not solve within 6 guesses.")

        time.sleep(3)
        browser.close()


if __name__ == "__main__":
    play(headless=False)