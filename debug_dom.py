"""
Run this FIRST, before player.py, to discover NYT's actual tile markup.
It prints out custom element tags, shadow root modes (open/closed), and
any elements that look like game tiles. Paste the output back so player.py
can be fixed with real selectors instead of guesses.

    python debug_dom.py
"""
import time
from playwright.sync_api import sync_playwright

WORDLE_URL = "https://www.nytimes.com/games/wordle/index.html"

# Uses the modern Element.getHTML({includeShadowRoots:true}) API (Chrome 125+)
# when available, which serializes open shadow roots. Closed shadow roots
# can't be read by ANY page-side JS, even this - if that's the case here,
# we'll fall back to Playwright's own locator engine (which CAN pierce
# open shadow roots, but also can't touch closed ones) to at least confirm
# whether tiles are clickable/visible.
INSPECT_JS = """
() => {
    const report = { customElements: [], shadowInfo: [], tileLikeMatches: [] };

    const all = document.querySelectorAll('*');
    const seenTags = new Set();
    for (const el of all) {
        const tag = el.tagName.toLowerCase();
        if (tag.includes('-') && !seenTags.has(tag)) {
            seenTags.add(tag);
            report.customElements.push(tag);
        }
    }

    function walk(root, path) {
        const els = root.querySelectorAll('*');
        for (const el of els) {
            if (el.shadowRoot) {
                report.shadowInfo.push({
                    tag: el.tagName.toLowerCase(),
                    mode: 'open',
                    path: path
                });
                walk(el.shadowRoot, path + ' > ' + el.tagName.toLowerCase() + '::shadow');
            }
            // Heuristic: look for anything tile/state related
            const attrs = el.getAttributeNames ? el.getAttributeNames() : [];
            const relevant = attrs.filter(a =>
                a.includes('state') || a.includes('letter') || a.toLowerCase().includes('tile')
            );
            if (relevant.length > 0 || (el.className && String(el.className).toLowerCase().includes('tile'))) {
                report.tileLikeMatches.push({
                    tag: el.tagName.toLowerCase(),
                    attrs: attrs.map(a => a + '=' + el.getAttribute(a)),
                    className: el.className ? String(el.className) : null,
                    text: (el.textContent || '').trim().slice(0, 10)
                });
            }
        }
    }
    walk(document, 'document');

    return report;
}
"""


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(WORDLE_URL, timeout=30000)
        time.sleep(2)

        # best-effort dismiss overlays so tiles are in a normal state
        try:
            page.keyboard.press("Escape")
            time.sleep(0.3)
        except Exception:
            pass

        page.screenshot(path="debug_before_type.png")
        print("Saved debug_before_type.png - look at it to confirm the board is visible.\n")

        report = page.evaluate(INSPECT_JS)

        print("=== Custom elements found on page ===")
        for tag in report["customElements"]:
            print(" ", tag)

        print("\n=== Elements with shadow roots (only OPEN ones are visible to JS) ===")
        for s in report["shadowInfo"]:
            print(f"  {s['tag']}  (mode={s['mode']})  path={s['path']}")

        print("\n=== Elements matching tile/state/letter heuristics ===")
        for m in report["tileLikeMatches"][:40]:
            print(f"  <{m['tag']}> class={m['className']} attrs={m['attrs']} text='{m['text']}'")

        if not report["tileLikeMatches"]:
            print("  (none found - board may be inside a CLOSED shadow root, "
                  "which page-side JS cannot see at all)")

        print("\nTry typing a guess now so we can see tile state after input...")
        for ch in "salet":
            page.keyboard.press(ch.upper())
            time.sleep(0.08)
        page.keyboard.press("Enter")
        time.sleep(2.5)
        page.screenshot(path="debug_after_guess.png")
        print("Saved debug_after_guess.png")

        report2 = page.evaluate(INSPECT_JS)
        print("\n=== tile/state matches AFTER typing a guess ===")
        for m in report2["tileLikeMatches"][:40]:
            print(f"  <{m['tag']}> class={m['className']} attrs={m['attrs']} text='{m['text']}'")

        input("\nPress Enter to close the browser...")
        browser.close()


if __name__ == "__main__":
    main()
