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

from solver import get_pattern, filter_candidates, naive_frequency_guess, WordleSolver, OPENERS


class TestGetPattern:
    def test_all_correct(self):
        assert get_pattern("tribe", "tribe") == (2, 2, 2, 2, 2)

    def test_all_absent(self):
        assert get_pattern("salet", "chomp") == (0, 0, 0, 0, 0)

    def test_mixed(self):
        assert get_pattern("trite", "tribe") == (2, 2, 2, 0, 2)

    def test_duplicate_letter_in_guess_single_in_answer(self):
        result = get_pattern("sassy", "chess")
        assert result[3] == 2 
        assert result.count(2) == 1 
        assert result.count(1) == 1

    def test_duplicate_letter_in_answer_single_in_guess(self):
        result = get_pattern("money", "geese")
        assert result[3] == 1

    def test_case_insensitive(self):
        assert get_pattern("TRIBE", "tribe") == (2, 2, 2, 2, 2)
        assert get_pattern("tribe", "TRIBE") == (2, 2, 2, 2, 2)

    def test_repeated_letter_correct_and_absent(self):
        assert get_pattern("erase", "arena") == (1, 2, 1, 0, 0)


class TestFilterCandidates:
    def test_filters_to_matching_only(self):
        candidates = ["tribe", "trice", "tripe", "brine", "crane"]
        result = filter_candidates(candidates, "trice", (2, 2, 2, 0, 2))
        assert "tribe" in result
        assert "trice" not in result

    def test_empty_result_when_nothing_matches(self):
        candidates = ["aaaaa", "bbbbb"]
        result = filter_candidates(candidates, "ccccc", (2, 2, 2, 2, 2))
        assert result == []

    def test_narrows_progressively(self):
        candidates = ["tribe", "trice", "tripe", "trine", "trite"]
        pattern = get_pattern("trice", "tribe")
        result = filter_candidates(candidates, "trice", pattern)
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
        assert naive_frequency_guess(["tribe", "trice"]) == "tribe"


class TestWordleSolverFallback:
    """WordleSolver should widen to the full allowed-guesses dictionary
    rather than giving up when the true answer isn't in the curated
    `possible` list - this happens for real, NYT has pulled answers from
    outside that original ~2309-word list."""

    def test_falls_back_when_possible_list_exhausted(self):
        s = WordleSolver()
        s.possible = ["tribe", "trice", "tripe"]
        s.candidates = list(s.possible)
        s.allowed = list(s.allowed) 

        s.update("salet", (0, 0, 0, 0, 0)) 
        assert s.used_fallback is True
        assert len(s.candidates) > 0
        for word in s.candidates:
            assert get_pattern("salet", word) == (0, 0, 0, 0, 0)

    def test_no_fallback_when_possible_list_suffices(self):
        s = WordleSolver()
        s.update(OPENERS[0], get_pattern(OPENERS[0], s.possible[0]))
        if s.candidates:
            assert s.used_fallback is False
