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


# Edge Case Tests for Quote Matcher

def test_quote_matching_with_special_characters(matcher):
    """Test quote matching with special characters and punctuation."""
    source = 'The court stated: "Due process of law" is a fundamental guarantee.'
    quote = '"Due process of law"'

    result = matcher.verify_quote(quote, source, "citation")
    assert result.found
    assert result.exact_match

    # Test with escaped quotes
    source = "The clause states: Rights and privileges shall be protected."
    quote = "Rights and privileges shall be protected"

    result = matcher.verify_quote(quote, source, "citation")
    assert result.found
    assert result.similarity >= 0.9


def test_quote_matching_unicode_handling(matcher):
    """Test quote matching with unicode characters and special symbols."""
    # Test with accented characters
    source = "The judgment was final: café and résumé were key terms."
    quote = "café and résumé"

    result = matcher.verify_quote(quote, source, "citation")
    assert result.found

    # Test with em-dashes and other unicode punctuation
    source = "The ruling—which was final—established precedent."
    quote = "The ruling — which was final"

    result = matcher.verify_quote(quote, source, "citation")
    assert result.found or result.similarity > 0.8


def test_empty_text_edge_case(matcher):
    """Test behavior with empty or minimal text."""
    # Empty quote
    result = matcher.verify_quote("", "Some source text", "citation")
    assert not result.found

    # Empty source
    result = matcher.verify_quote("some quote", "", "citation")
    assert not result.found

    # Both empty
    result = matcher.verify_quote("", "", "citation")
    assert not result.found

    # Single character
    source = "a"
    quote = "a"
    result = matcher.verify_quote(quote, source, "citation")
    assert result.found


def test_very_long_quotes(matcher):
    """Test with extremely long quotes and source texts."""
    # Long quote (1000+ characters)
    long_quote = " ".join(["word"] * 200)
    long_source = "prefix " + long_quote + " suffix"

    result = matcher.verify_quote(long_quote, long_source, "citation")
    assert result.found
    assert result.similarity >= 0.95

    # Very long source with multiple matches
    repeated_text = "The clause states: fundamental right. " * 50
    quote = "fundamental right"

    result = matcher.verify_quote(quote, repeated_text, "citation")
    assert result.found
    assert len(result.matches) > 1


def test_pinpoint_extraction_edge_cases(matcher):
    """Test pinpoint quote extraction with edge cases."""
    # Quote at the very beginning
    source = "First words are important. Then comes the rest."
    quote = "First words are"

    result = matcher.verify_quote(quote, source, "citation")
    assert result.found
    assert result.matches[0].position == 0

    # Quote at the very end
    source = "The beginning is long. important ending"
    quote = "important ending"

    result = matcher.verify_quote(quote, source, "citation")
    assert result.found
    assert result.matches[0].position > 0

    # Quote spanning multiple sentences
    source = "This is sentence one. This is sentence two. This is three."
    quote = "sentence one. This is sentence two"

    result = matcher.verify_quote(quote, source, "citation")
    assert result.found or result.similarity > 0.8

    # Context extraction at boundaries
    matcher_small_context = QuoteMatcher(context_chars=10)
    result = matcher_small_context.verify_quote("important", "very important word here", "citation")
    assert result.found
    # Context should be limited
    if result.matches:
        context_length = len(result.matches[0].context_before) + len(result.matches[0].context_after)
        assert context_length <= 30  # Small context window
