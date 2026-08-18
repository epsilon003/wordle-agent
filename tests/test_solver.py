"""
Tests for the core solver logic - pattern computation and candidate
filtering. Duplicate-letter handling is the classic Wordle correctness
trap (Wordle's actual rule: green matches consume a letter instance
first, then yellow matches consume from what's left), so it gets
dedicated coverage here.

Run with: pytest tests/
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from solver import get_pattern, filter_candidates, naive_frequency_guess


class TestGetPattern:
    def test_all_correct(self):
        assert get_pattern("tribe", "tribe") == (2, 2, 2, 2, 2)

    def test_all_absent(self):
        # "salet" vs "chomp" share no letters at all
        assert get_pattern("salet", "chomp") == (0, 0, 0, 0, 0)

    def test_mixed(self):
        # trite vs tribe: t-r-i correct, t absent (no 2nd t in answer), e correct
        assert get_pattern("trite", "tribe") == (2, 2, 2, 0, 2)

    def test_duplicate_letter_in_guess_single_in_answer(self):
        # guess "sassy" has three s's, answer "chess" has only one s,
        # positioned at index 3. Only that one should register (not
        # absent, not present) - the other two guessed s's must be absent.
        # sassy: s-a-s-s-y, chess: c-h-e-s-s
        # index0 s vs c -> not correct; is there an s left in "chess"? yes (2 of them) -> present
        # index1 a vs h -> absent (no a in chess)
        # index2 s vs e -> after first s consumed one, one s remains -> present
        # index3 s vs s -> correct match, consumes an s from remaining count
        # index4 y vs s -> absent
        result = get_pattern("sassy", "chess")
        assert result[3] == 2  # the aligned s at index 3 is correct
        assert result.count(2) == 1  # only one correct
        # total s's in answer = 2; one consumed by the correct match at
        # index 3, one remains to be claimed by an earlier guessed s
        assert result.count(1) == 1  # exactly one of the other s's is "present"

    def test_duplicate_letter_in_answer_single_in_guess(self):
        # guess has one 'e', answer "cheese" has three... but Wordle
        # words are 5 letters; use "geese" (g-e-e-s-e) as answer with
        # three e's, guess "crepe" (one e at index... ) simpler: guess
        # "money" vs answer "geese" - guess has one 'e' at index 3.
        result = get_pattern("money", "geese")
        # 'e' in guess at index 3 vs geese[3] = 's' -> not correct;
        # geese has e's available -> present
        assert result[3] == 1

    def test_case_insensitive(self):
        assert get_pattern("TRIBE", "tribe") == (2, 2, 2, 2, 2)
        assert get_pattern("tribe", "TRIBE") == (2, 2, 2, 2, 2)

    def test_repeated_letter_correct_and_absent(self):
        # guess "erase" vs answer "arena"
        # erase: e-r-a-s-e, arena: a-r-e-n-a
        # index0 e vs a -> arena DOES contain an 'e' (at index 2) -> present (1)
        # index1 r vs r -> correct (2)
        # index2 a vs e -> arena has 2 a's, none consumed yet -> present (1)
        # index3 s vs n -> absent (0), no s in arena
        # index4 e vs a -> that one 'e' in arena was already claimed by
        #   index0's guessed e -> absent (0)
        assert get_pattern("erase", "arena") == (1, 2, 1, 0, 0)


class TestFilterCandidates:
    def test_filters_to_matching_only(self):
        candidates = ["tribe", "trice", "tripe", "brine", "crane"]
        # guess "trice" against unknown answer that gives this exact pattern
        # for "tribe": (2,2,2,0,2) means position 3 ('c' vs actual) absent
        result = filter_candidates(candidates, "trice", (2, 2, 2, 0, 2))
        assert "tribe" in result
        assert "trice" not in result  # trice vs itself would be all-correct, not this pattern

    def test_empty_result_when_nothing_matches(self):
        candidates = ["aaaaa", "bbbbb"]
        result = filter_candidates(candidates, "ccccc", (2, 2, 2, 2, 2))
        assert result == []

    def test_narrows_progressively(self):
        candidates = ["tribe", "trice", "tripe", "trine", "trite"]
        pattern = get_pattern("trice", "tribe")
        result = filter_candidates(candidates, "trice", pattern)
        # every remaining candidate must itself produce the same pattern
        for word in result:
            assert get_pattern("trice", word) == pattern


class TestNaiveFrequencyGuess:
    def test_returns_a_candidate(self):
        candidates = ["tribe", "trice", "tripe"]
        guess = naive_frequency_guess(candidates)
        assert guess in candidates

    def test_single_candidate_shortcut(self):
        assert naive_frequency_guess(["tribe"]) == "tribe"

    def test_two_candidates_returns_first(self):
        # len <= 2 short-circuits to candidates[0]
        assert naive_frequency_guess(["tribe", "trice"]) == "tribe"
