"""Quote verification and matching for legal citations.

This module provides tools for verifying that quotes accurately appear in cited
cases, essential for maintaining academic integrity in legal scholarship.
"""

import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class QuoteMatch:
    """A match found for a quote in source text."""

    found: bool
    exact_match: bool
    similarity: float  # 0-1 score
    position: int  # Character position in source
    matched_text: str  # What was actually found
    context_before: str  # Text before the quote
    context_after: str  # Text after the quote
    differences: list[str]  # List of differences if not exact


@dataclass
class QuoteVerificationResult:
    """Result of verifying a quote against a source."""

    quote: str
    citation: str
    found: bool
    exact_match: bool
    similarity: float
    matches: list[QuoteMatch]
    warnings: list[str]
    recommendation: str


class QuoteMatcher:
    """Matcher for verifying legal quotes against source text."""

    def __init__(
        self,
        exact_match_threshold: float = 1.0,
        fuzzy_match_threshold: float = 0.85,
        context_chars: int = 200,
    ) -> None:
        """Initialize the quote matcher.

        Args:
            exact_match_threshold: Similarity threshold for exact match (1.0)
            fuzzy_match_threshold: Minimum similarity for fuzzy match (0.85)
            context_chars: Characters of context to include before/after quote
        """
        self.exact_threshold = exact_match_threshold
        self.fuzzy_threshold = fuzzy_match_threshold
        self.context_chars = context_chars

    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Strip HTML tags if present
        text = re.sub(r"<[^>]+>", " ", text)
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove line breaks
        text = text.replace("\n", " ")
        # Remove smart quotes and replace with standard quotes
        text = text.replace(""", '"').replace(""", '"')
        text = text.replace("'", "'").replace("'", "'")
        # Strip leading/trailing whitespace
        text = text.strip()
        return text

    def normalize_for_fuzzy_match(self, text: str) -> str:
        """Normalize text for fuzzy matching (more aggressive).

        Args:
            text: Text to normalize

        Returns:
            Normalized text for fuzzy matching
        """
        text = self.normalize_text(text)
        # Case insensitive for fuzzy matching
        text = text.lower()
        # Remove punctuation variations
        text = re.sub(r'[""''`]', '"', text)
        # Normalize ellipsis
        text = re.sub(r'\.{3,}|\.\s\.\s\.', '...', text)
        return text

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score from 0 to 1
        """
        return SequenceMatcher(None, text1, text2).ratio()

    def find_quote_exact(self, quote: str, source: str) -> list[QuoteMatch]:
        """Find exact matches of quote in source text.

        Args:
            quote: Quote to search for
            source: Source text to search in

        Returns:
            List of exact matches found
        """
        matches = []

        # Normalize both texts but preserve source structure
        normalized_quote = self.normalize_text(quote)
        normalized_source = self.normalize_text(source)

        # Search for exact matches (case-sensitive)
        pattern = re.escape(normalized_quote)
        for match in re.finditer(pattern, normalized_source, re.IGNORECASE):
            position = match.start()

            # Extract context
            context_start = max(0, position - self.context_chars)
            context_end = min(len(normalized_source), match.end() + self.context_chars)

            context_before = normalized_source[context_start:position]
            context_after = normalized_source[match.end():context_end]

            matches.append(
                QuoteMatch(
                    found=True,
                    exact_match=True,
                    similarity=1.0,
                    position=position,
                    matched_text=match.group(),
                    context_before=context_before,
                    context_after=context_after,
                    differences=[],
                )
            )

        return matches

    def find_quote_fuzzy(
        self,
        quote: str,
        source: str,
        max_matches: int = 5,
    ) -> list[QuoteMatch]:
        """Find fuzzy matches of quote in source text.

        Uses sliding window approach to find similar passages.

        Args:
            quote: Quote to search for
            source: Source text to search in
            max_matches: Maximum number of fuzzy matches to return

        Returns:
            List of fuzzy matches found, sorted by similarity
        """
        normalized_quote = self.normalize_for_fuzzy_match(quote)
        normalized_source = self.normalize_for_fuzzy_match(source)

        quote_len = len(normalized_quote)
        source_len = len(normalized_source)

        if quote_len > source_len:
            return []

        matches: list[tuple[float, int, str]] = []  # (similarity, position, text)

        # Sliding window approach
        window_size = quote_len
        tolerance = int(quote_len * 0.2)  # Allow 20% size variation

        for start in range(0, source_len - window_size + tolerance + 1, max(1, quote_len // 4)):
            for size in range(
                max(window_size - tolerance, 1),
                min(window_size + tolerance, source_len - start) + 1,
            ):
                end = start + size
                window = normalized_source[start:end]

                similarity = self.calculate_similarity(normalized_quote, window)

                if similarity >= self.fuzzy_threshold:
                    # Get the original text (not normalized)
                    original_text = source[start:end]
                    matches.append((similarity, start, original_text))

        # Sort by similarity (descending) and remove duplicates
        matches.sort(reverse=True, key=lambda x: x[0])
        unique_matches: list[QuoteMatch] = []
        seen_positions: set[int] = set()

        for similarity, position, matched_text in matches[:max_matches]:
            # Skip if too close to a previous match
            if any(abs(position - seen_pos) < quote_len // 2 for seen_pos in seen_positions):
                continue

            seen_positions.add(position)

            # Extract context
            context_start = max(0, position - self.context_chars)
            context_end = min(len(source), position + len(matched_text) + self.context_chars)

            context_before = source[context_start:position]
            context_after = source[position + len(matched_text):context_end]

            # Find differences
            differences = self._find_differences(quote, matched_text)

            unique_matches.append(
                QuoteMatch(
                    found=True,
                    exact_match=False,
                    similarity=similarity,
                    position=position,
                    matched_text=matched_text,
                    context_before=context_before,
                    context_after=context_after,
                    differences=differences,
                )
            )

        return unique_matches

    def _find_differences(self, expected: str, actual: str) -> list[str]:
        """Find specific differences between expected and actual text.

        Args:
            expected: Expected text (quote)
            actual: Actual text found

        Returns:
            List of difference descriptions
        """
        differences = []

        # Normalize for comparison
        norm_expected = self.normalize_text(expected)
        norm_actual = self.normalize_text(actual)

        # Check length difference
        len_diff = abs(len(norm_expected) - len(norm_actual))
        if len_diff > 0:
            differences.append(f"Length differs by {len_diff} characters")

        # Check word count
        expected_words = norm_expected.split()
        actual_words = norm_actual.split()
        word_diff = abs(len(expected_words) - len(actual_words))
        if word_diff > 0:
            differences.append(f"Word count differs by {word_diff} words")

        # Find mismatched words
        matcher = SequenceMatcher(None, expected_words, actual_words)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "replace":
                differences.append(
                    f"Words differ: '{' '.join(expected_words[i1:i2])}' vs '{' '.join(actual_words[j1:j2])}'"
                )
            elif tag == "delete":
                differences.append(f"Missing words: '{' '.join(expected_words[i1:i2])}'")
            elif tag == "insert":
                differences.append(f"Extra words: '{' '.join(actual_words[j1:j2])}'")

        return differences[:5]  # Limit to 5 most significant differences

    def verify_quote(
        self,
        quote: str,
        source: str,
        citation: str,
    ) -> QuoteVerificationResult:
        """Verify a quote against source text.

        Args:
            quote: The quote to verify
            source: The source text to check against
            citation: The citation being verified

        Returns:
            QuoteVerificationResult with detailed findings
        """
        if not quote.strip():
            logger.warning("Empty quote provided; skipping verification")
            return QuoteVerificationResult(
                quote=quote,
                citation=citation,
                found=False,
                exact_match=False,
                similarity=0.0,
                matches=[],
                warnings=["No quote provided for verification"],
                recommendation="Provide a non-empty quote to verify",
            )

        logger.info(f"Verifying quote ({len(quote)} chars) against source ({len(source)} chars)")

        # First try exact match
        exact_matches = self.find_quote_exact(quote, source)

        if exact_matches:
            logger.info(f"Found {len(exact_matches)} exact match(es)")
            return QuoteVerificationResult(
                quote=quote,
                citation=citation,
                found=True,
                exact_match=True,
                similarity=1.0,
                matches=exact_matches,
                warnings=[],
                recommendation="Quote verified exactly in source",
            )

        # If no exact match, try fuzzy matching
        logger.info("No exact match, attempting fuzzy match...")
        fuzzy_matches = self.find_quote_fuzzy(quote, source)

        if fuzzy_matches:
            best_match = fuzzy_matches[0]
            logger.info(
                f"Found {len(fuzzy_matches)} fuzzy match(es), "
                f"best similarity: {best_match.similarity:.2%}"
            )

            warnings = []
            if best_match.similarity < 0.95:
                warnings.append("Quote differs from source text")
            if best_match.differences:
                warnings.append(f"Differences found: {len(best_match.differences)}")

            recommendation = (
                "Quote found with minor differences - review recommended"
                if best_match.similarity >= 0.95
                else "Quote significantly differs from source - verify carefully"
            )

            return QuoteVerificationResult(
                quote=quote,
                citation=citation,
                found=True,
                exact_match=False,
                similarity=best_match.similarity,
                matches=fuzzy_matches,
                warnings=warnings,
                recommendation=recommendation,
            )

        # No matches found
        logger.warning("No matches found for quote")
        return QuoteVerificationResult(
            quote=quote,
            citation=citation,
            found=False,
            exact_match=False,
            similarity=0.0,
            matches=[],
            warnings=["Quote not found in source text"],
            recommendation="Quote could not be verified - check citation and text",
        )
