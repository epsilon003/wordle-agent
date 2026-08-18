"""Benchmark the entropy solver against a naive frequency baseline, and
report against 3Blue1Brown's published optimal (~3.42 avg guesses,
https://www.youtube.com/watch?v=v68zYyaEmEA - solving Wordle using
information theory).
"""
import random
import time
from solver import WordleSolver, NaiveFrequencySolver, get_pattern, load_words

PUBLISHED_OPTIMAL_AVG_GUESSES = 3.42  # 3b1b's information-theoretic solver


def play_one(solver_factory, answer, verbose=False):
    s = solver_factory()
    for turn in range(1, 7):
        guess = s.next_guess()
        pattern = get_pattern(guess, answer)
        if verbose:
            print(f"  turn {turn}: {guess} -> {pattern}")
        if s.is_solved(pattern):
            return turn
        s.update(guess, pattern)
    return None  # failed within 6


def run_benchmark(solver_factory, sample, label):
    t0 = time.time()
    results = [play_one(solver_factory, ans) for ans in sample]
    elapsed = time.time() - t0

    solved = [r for r in results if r is not None]
    fails = [ans for ans, r in zip(sample, results) if r is None]
    avg = sum(solved) / len(solved) if solved else float("nan")

    print(f"\n=== {label} ===")
    print(f"Solved {len(solved)}/{len(sample)}")
    print(f"Average guesses: {avg:.3f}")
    print(f"Max guesses: {max(solved) if solved else '-'}")
    print(f"Failures: {fails}")
    print(f"Time: {elapsed:.1f}s ({elapsed/len(sample):.2f}s/game)")
    return {
        "label": label,
        "solved": len(solved),
        "total": len(sample),
        "avg_guesses": avg,
        "max_guesses": max(solved) if solved else None,
    }


if __name__ == "__main__":
    _, possible = load_words()
    random.seed(42)
    sample = random.sample(possible, 60)

    print("Sample run with verbose output (entropy solver):")
    play_one(WordleSolver, random.choice(sample), verbose=True)

    entropy_result = run_benchmark(WordleSolver, sample, "Entropy solver (this project)")
    naive_result = run_benchmark(NaiveFrequencySolver, sample, "Naive frequency baseline")

    print("\n=== Comparison ===")
    print(f"{'Solver':<32}{'Win rate':<12}{'Avg guesses':<14}")
    print(f"{entropy_result['label']:<32}"
          f"{entropy_result['solved']}/{entropy_result['total']:<10}"
          f"{entropy_result['avg_guesses']:.3f}")
    print(f"{naive_result['label']:<32}"
          f"{naive_result['solved']}/{naive_result['total']:<10}"
          f"{naive_result['avg_guesses']:.3f}")
    print(f"{'Published optimal (3b1b)':<32}{'-':<12}{PUBLISHED_OPTIMAL_AVG_GUESSES:.3f}")
