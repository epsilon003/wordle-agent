"""
Entropy-based Wordle solver.

Pattern encoding per letter: 0 = absent (grey), 1 = present (yellow), 2 = correct (green)
Returned as a tuple of 5 ints, e.g. (2,0,1,0,0).
"""
import math
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent

# Good fixed openers (pre-computed as high-entropy first guesses against the
# NYT solution list). Using a fixed opener avoids recomputing entropy over
# ~13k x 2.3k combinations on every run.
OPENERS = ["salet", "crane", "trace", "slate", "roate"]

# Once the candidate set shrinks to this size or fewer, restrict guesses to
# the candidates themselves rather than the full dictionary. Pure entropy
# maximization will sometimes prefer a non-candidate "probe" word that
# splits a small remaining set most evenly - which is optimal for expected
# total guesses over many games, but gives up any chance of winning that
# turn. Below this threshold we trade a sliver of long-run optimality for
# always leaving a shot at solving immediately.
CANDIDATE_ONLY_THRESHOLD = 10


def load_words():
    allowed = (DATA_DIR / "allowed_words.txt").read_text().split()
    possible = (DATA_DIR / "possible_words.txt").read_text().split()
    return allowed, possible


def get_pattern(guess: str, answer: str) -> tuple:
    """Compute the Wordle feedback pattern for `guess` against `answer`."""
    guess = guess.lower()
    answer = answer.lower()
    result = [0] * 5
    answer_counts = Counter(answer)

    # First pass: greens
    for i in range(5):
        if guess[i] == answer[i]:
            result[i] = 2
            answer_counts[guess[i]] -= 1

    # Second pass: yellows
    for i in range(5):
        if result[i] == 0 and answer_counts[guess[i]] > 0:
            result[i] = 1
            answer_counts[guess[i]] -= 1

    return tuple(result)


def filter_candidates(candidates, guess, pattern):
    """Keep only candidates consistent with the observed pattern for guess."""
    return [w for w in candidates if get_pattern(guess, w) == tuple(pattern)]


def entropy_of_guess(guess, candidates):
    """Shannon entropy (bits) of the pattern distribution `guess` induces
    over the current candidate set. Higher = more informative."""
    buckets = Counter()
    for ans in candidates:
        buckets[get_pattern(guess, ans)] += 1
    n = len(candidates)
    ent = 0.0
    for count in buckets.values():
        p = count / n
        ent -= p * math.log2(p)
    return ent


def best_guess(candidates, guess_pool, max_pool=2500):
    """Pick the guess (from guess_pool) that maximizes expected information
    gain against the current candidate set. If a guess is itself a
    candidate, it's given a tiny bonus so we prefer guesses that could
    directly be the answer when entropy ties.
    """
    if len(candidates) <= 2:
        return candidates[0]

    candidate_set = set(candidates)
    # Cap pool size for speed when candidate set is huge (first guess case
    # is short-circuited by OPENERS anyway).
    pool = guess_pool if len(guess_pool) <= max_pool else candidates + \
        [w for w in guess_pool if w not in candidate_set][: max_pool - len(candidates)]

    best_word, best_score = None, -1.0
    for g in pool:
        score = entropy_of_guess(g, candidates)
        if g in candidate_set:
            score += 1e-6
        if score > best_score:
            best_word, best_score = g, score
    return best_word


class WordleSolver:
    def __init__(self):
        self.allowed, self.possible = load_words()
        self.candidates = list(self.possible)
        self.guess_count = 0
        self.history = []          # [(guess, pattern), ...] - full game so far
        self.used_fallback = False # True once we've had to widen beyond `possible`

    def next_guess(self) -> str:
        if self.guess_count == 0:
            self.guess_count += 1
            return OPENERS[0]
        self.guess_count += 1
        if len(self.candidates) <= CANDIDATE_ONLY_THRESHOLD:
            return best_guess(self.candidates, self.candidates)
        return best_guess(self.candidates, self.allowed)

    def update(self, guess: str, pattern) -> None:
        """Narrow candidates given the feedback pattern for `guess`."""
        pattern = tuple(pattern)
        self.history.append((guess, pattern))
        self.candidates = filter_candidates(self.candidates, guess, pattern)

        if not self.candidates:
            # The true answer isn't in `possible` at all - NYT has been
            # known to pull answers from a wider word bank than the
            # original ~2309-word curated list this solver is seeded
            # with. Rather than give up, widen the search to the full
            # ~13k-word allowed-guesses dictionary, re-applying every
            # constraint seen so far.
            self.used_fallback = True
            fallback = list(self.allowed)
            for g, p in self.history:
                fallback = filter_candidates(fallback, g, p)
            self.candidates = fallback

    def is_solved(self, pattern) -> bool:
        return tuple(pattern) == (2, 2, 2, 2, 2)


def naive_frequency_guess(candidates):
    """Baseline heuristic: score each candidate by summing, for each
    letter it contains, how often that letter appears in that exact
    position across the remaining candidates. No information-theoretic
    reasoning at all - just "pick the word that looks most typical of
    what's left." Always guesses from the candidate list itself (never
    probes with an out-of-pool word)."""
    if len(candidates) <= 2:
        return candidates[0]

    position_counts = [Counter(word[i] for word in candidates) for i in range(5)]

    best_word, best_score = None, -1
    for word in candidates:
        score = sum(position_counts[i][ch] for i, ch in enumerate(word))
        if score > best_score:
            best_word, best_score = word, score
    return best_word


class NaiveFrequencySolver:
    """Baseline for benchmarking against WordleSolver. Same opener, same
    candidate-filtering, but picks each subsequent guess by raw
    letter-position frequency instead of entropy - no lookahead, no
    information theory. See simulate.py for the head-to-head comparison."""

    def __init__(self):
        self.allowed, self.possible = load_words()
        self.candidates = list(self.possible)
        self.guess_count = 0

    def next_guess(self) -> str:
        if self.guess_count == 0:
            self.guess_count += 1
            return OPENERS[0]
        self.guess_count += 1
        return naive_frequency_guess(self.candidates)

    def update(self, guess: str, pattern) -> None:
        self.candidates = filter_candidates(self.candidates, guess, tuple(pattern))

    def is_solved(self, pattern) -> bool:
        return tuple(pattern) == (2, 2, 2, 2, 2)
