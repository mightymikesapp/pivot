"""Tests for quote matching."""

import pytest

from app.analysis.quote_matcher import QuoteMatcher


@pytest.fixture
def matcher():
    return QuoteMatcher()

def test_normalize_text(matcher):
    text = "  Hello   World  \n "
    assert matcher.normalize_text(text) == "Hello World"

    text = '<p>Hello</p> "World"'
    assert matcher.normalize_text(text) == 'Hello "World"'

def test_calculate_similarity(matcher):
    assert matcher.calculate_similarity("abc", "abc") == 1.0
    assert matcher.calculate_similarity("abc", "def") == 0.0
    assert 0.0 < matcher.calculate_similarity("abc", "abd") < 1.0

def test_find_quote_exact(matcher):
    source = "This is a test of the emergency broadcast system."
    quote = "test of the emergency"

    matches = matcher.find_quote_exact(quote, source)
    assert len(matches) == 1
    assert matches[0].exact_match
    assert matches[0].matched_text == "test of the emergency"
    assert matches[0].position == 10

def test_find_quote_exact_case_insensitive(matcher):
    source = "This is a TEST of the emergency broadcast system."
    quote = "test of the emergency"

    matches = matcher.find_quote_exact(quote, source)
    assert len(matches) == 1
    assert matches[0].exact_match

def test_find_quote_fuzzy(matcher):
    source = "The quick brown fox jumps over the lazy dog."
    quote = "quick brown fox jumped over" # "jumps" vs "jumped"

    matches = matcher.find_quote_fuzzy(quote, source)
    assert len(matches) > 0
    assert not matches[0].exact_match
    assert matches[0].similarity > 0.8

def test_verify_quote_exact(matcher):
    source = "The Constitution of the United States."
    quote = "Constitution of the United"

    result = matcher.verify_quote(quote, source, "citation")
    assert result.found
    assert result.exact_match
    assert result.similarity == 1.0

def test_verify_quote_fuzzy(matcher):
    source = "The Constitution of the United States."
    quote = "Constitution for the United" # "of" vs "for"

    result = matcher.verify_quote(quote, source, "citation")
    assert result.found
    assert not result.exact_match
    assert result.similarity > 0.8
    assert len(result.warnings) > 0

def test_verify_quote_not_found(matcher):
    source = "The Constitution of the United States."
    quote = "Declaration of Independence"

    result = matcher.verify_quote(quote, source, "citation")
    assert not result.found
    assert result.similarity == 0.0

def test_find_differences(matcher):
    diffs = matcher._find_differences("Hello World", "Hello there World")
    assert any("Extra words" in d for d in diffs)

    diffs = matcher._find_differences("Hello World", "Hello")
    assert any("Missing words" in d for d in diffs)

    diffs = matcher._find_differences("Hello World", "Hello Earth")
    assert any("Words differ" in d for d in diffs)
