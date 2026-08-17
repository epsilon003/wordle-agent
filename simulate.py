"""Simulate the solver against every possible answer to sanity-check it."""
import random
import time
from solver import WordleSolver, get_pattern, load_words

def play_one(answer, verbose=False):
    s = WordleSolver()
    for turn in range(1, 7):
        guess = s.next_guess()
        pattern = get_pattern(guess, answer)
        if verbose:
            print(f"  turn {turn}: {guess} -> {pattern}")
        if s.is_solved(pattern):
            return turn
        s.update(guess, pattern)
    return None  # failed within 6

if __name__ == "__main__":
    allowed, possible = load_words()
    random.seed(42)
    sample = random.sample(possible, 60)  # subsample for speed in this demo

    print("Sample run with verbose output:")
    play_one(random.choice(sample), verbose=True)
    print()

    t0 = time.time()
    results = []
    fails = []
    for ans in sample:
        r = play_one(ans)
        results.append(r)
        if r is None:
            fails.append(ans)
    elapsed = time.time() - t0

    solved = [r for r in results if r is not None]
    print(f"Solved {len(solved)}/{len(sample)} in sample")
    print(f"Average guesses: {sum(solved)/len(solved):.3f}")
    print(f"Max guesses: {max(solved)}")
    print(f"Failures: {fails}")
    print(f"Time: {elapsed:.1f}s for {len(sample)} games ({elapsed/len(sample):.2f}s/game)")
