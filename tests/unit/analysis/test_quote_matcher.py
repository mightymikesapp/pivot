"""Unit tests for quote matcher fuzzy matching utilities."""

import pytest

from app.analysis.quote_matcher import QuoteMatcher


def test_normalize_for_fuzzy_match_handles_ellipsis_and_punctuation() -> None:
    matcher = QuoteMatcher()
    text = "“Wait . . . what?” asked the judge…"

    normalized = matcher.normalize_for_fuzzy_match(text)

    assert normalized == '"wait ... what?" asked the judge...'


def test_find_quote_fuzzy_returns_empty_when_quote_longer_than_source() -> None:
    matcher = QuoteMatcher()
    quote = "This quote is definitely longer than the source."
    source = "short source"

    matches = matcher.find_quote_fuzzy(quote, source)

    assert matches == []


def test_find_quote_fuzzy_respects_threshold_and_orders_matches() -> None:
    matcher = QuoteMatcher(fuzzy_match_threshold=0.88, context_chars=10)
    quote = "alpha beta gamma delta"
    source = (
        "alpha beta gamma delta filler text "
        "alfa beta gamms delta and unrelated trailing words"
    )

    matches = matcher.find_quote_fuzzy(quote, source, max_matches=3)

    assert len(matches) == 2
    assert matches[0].similarity >= matches[1].similarity
    assert matches[0].position == 0
    assert matches[1].position > len(quote)
    assert all(match.similarity >= matcher.fuzzy_threshold for match in matches)
    assert all(not match.exact_match for match in matches)
    assert matches[0].matched_text.startswith("alpha beta gamma delta")
    assert "alpha beta" in matches[1].matched_text
    assert matches[0].context_before == ""
    assert matches[0].context_after.startswith(" filler")
