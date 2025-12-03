"""Treatment classification for legal citations.

This module analyzes how citing cases treat a target case, classifying treatment as:
- Positive: Case is followed, affirmed, applied, or relied upon
- Negative: Case is overruled, questioned, criticized, or limited
- Neutral: Case is cited without clear positive or negative treatment
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TreatmentType(Enum):
    """Classification of how a case treats another case."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


@dataclass
class TreatmentSignal:
    """A treatment signal found in text."""

    signal: str
    treatment_type: TreatmentType
    position: int
    context: str


@dataclass
class TreatmentAnalysis:
    """Analysis of treatment for a single citing case."""

    case_name: str
    case_id: str
    citation: str
    treatment_type: TreatmentType
    confidence: float
    signals_found: list[TreatmentSignal]
    excerpt: str
    date_filed: str | None = None


@dataclass
class AggregatedTreatment:
    """Aggregated treatment analysis across multiple citing cases."""

    citation: str
    is_good_law: bool
    confidence: float
    total_citing_cases: int
    positive_count: int
    negative_count: int
    neutral_count: int
    unknown_count: int
    negative_treatments: list[TreatmentAnalysis]
    positive_treatments: list[TreatmentAnalysis]
    summary: str


# Treatment signal patterns with weights
NEGATIVE_SIGNALS = {
    r"\boverruled\b": ("overruled", 1.0),
    r"\babrogated\b": ("abrogated", 1.0),
    r"\boverturned\b": ("overturned", 1.0),
    r"\breversed\b": ("reversed", 0.9),
    r"\bdisapproved\b": ("disapproved", 0.85),
    r"\brejected\b": ("rejected", 0.8),
    r"\bquestioned\b": ("questioned", 0.7),
    r"\bcriticized\b": ("criticized", 0.7),
    r"\blimited\s+to\b": ("limited to", 0.7),
    r"\bdistinguished\b": ("distinguished", 0.5),  # Can be neutral, but often negative
    r"\bno\s+longer\s+good\s+law\b": ("no longer good law", 1.0),
    r"\bnot\s+followed\b": ("not followed", 0.85),
    r"\bsuperseded\b": ("superseded", 0.95),
    r"\bvacated\b": ("vacated", 0.9),
}

POSITIVE_SIGNALS = {
    r"\bfollowed\b": ("followed", 0.9),
    r"\baffirmed\b": ("affirmed", 0.9),
    r"\badopted\b": ("adopted", 0.85),
    r"\bapplied\b": ("applied", 0.8),
    r"\brelied\s+(?:up)?on\b": ("relied on", 0.85),
    r"\bconsistent\s+with\b": ("consistent with", 0.7),
    r"\bin\s+accord\s+with\b": ("in accord with", 0.8),
    r"\bagree\s+with\b": ("agree with", 0.8),
    r"\bsupport(?:s|ed|ing)\b": ("supports", 0.7),
    r"\bupheld\b": ("upheld", 0.9),
    r"\bconfirmed\b": ("confirmed", 0.85),
}


class TreatmentClassifier:
    """Classifier for determining how cases treat other cases."""

    def __init__(self) -> None:
        """Initialize the treatment classifier."""
        self.negative_patterns = {
            re.compile(pattern, re.IGNORECASE): (signal, weight)
            for pattern, (signal, weight) in NEGATIVE_SIGNALS.items()
        }
        self.positive_patterns = {
            re.compile(pattern, re.IGNORECASE): (signal, weight)
            for pattern, (signal, weight) in POSITIVE_SIGNALS.items()
        }

    def should_fetch_full_text(
        self,
        initial_analysis: "TreatmentAnalysis",
        strategy: str,
    ) -> bool:
        """Determine if full text should be fetched for deeper analysis.

        Args:
            initial_analysis: Initial analysis based on snippets
            strategy: Fetching strategy ('always', 'smart', 'negative_only', 'never')

        Returns:
            True if full text should be fetched
        """
        if strategy == "never":
            return False

        if strategy == "always":
            return True

        if strategy == "negative_only":
            return initial_analysis.treatment_type == TreatmentType.NEGATIVE

        if strategy == "smart":
            # Fetch if:
            # 1. Negative signals found (high priority)
            # 2. Low confidence (ambiguous)
            # 3. Unknown treatment (needs more context)
            return (
                initial_analysis.treatment_type == TreatmentType.NEGATIVE
                or initial_analysis.confidence < 0.6
                or initial_analysis.treatment_type == TreatmentType.UNKNOWN
            )

        return False

    def extract_signals(self, text: str, citation: str) -> list[TreatmentSignal]:
        """Extract treatment signals from text mentioning the citation.

        Args:
            text: Text to analyze
            citation: The citation being analyzed

        Returns:
            List of treatment signals found
        """
        signals: list[TreatmentSignal] = []

        # Extract context windows around the citation
        contexts = self._extract_citation_contexts(text, citation)

        for context, position in contexts:
            # Check for negative signals
            for pattern, (signal, weight) in self.negative_patterns.items():
                if pattern.search(context):
                    signals.append(
                        TreatmentSignal(
                            signal=signal,
                            treatment_type=TreatmentType.NEGATIVE,
                            position=position,
                            context=context[:200],  # First 200 chars
                        )
                    )

            # Check for positive signals
            for pattern, (signal, weight) in self.positive_patterns.items():
                if pattern.search(context):
                    signals.append(
                        TreatmentSignal(
                            signal=signal,
                            treatment_type=TreatmentType.POSITIVE,
                            position=position,
                            context=context[:200],
                        )
                    )

        return signals

    def classify_treatment(
        self,
        citing_case: CourtListenerCase,
        target_citation: str,
        full_text: str | None = None,
    ) -> TreatmentAnalysis:
        """Classify how a citing case treats the target citation.

        Args:
            citing_case: Dictionary containing citing case information
            target_citation: The citation being analyzed
            full_text: Optional full opinion text for deeper analysis

        Returns:
            TreatmentAnalysis with classification and confidence
        """
        # Use full text if provided, otherwise extract from case metadata
        if full_text:
            text = full_text
            logger.debug(f"Using full text ({len(text)} chars) for analysis")
        else:
            # Extract text to analyze from multiple possible sources
            # CourtListener V4 API structure
            text_parts = []

            # Get syllabus (case summary)
            if citing_case.get("syllabus"):
                text_parts.append(citing_case["syllabus"])

            # Get snippets from nested opinions array
            if citing_case.get("opinions"):
                for opinion in citing_case["opinions"]:
                    if opinion.get("snippet"):
                        text_parts.append(opinion["snippet"])

            # Legacy/fallback fields
            if citing_case.get("plain_text"):
                text_parts.append(citing_case["plain_text"])
            if citing_case.get("snippet"):
                text_parts.append(citing_case["snippet"])
            if citing_case.get("text"):
                text_parts.append(citing_case["text"])

            # Combine all text
            text = "\n\n".join(text_parts) if text_parts else ""
            logger.debug(f"Using snippet text ({len(text)} chars) for analysis")

        # Extract signals
        signals = self.extract_signals(text, target_citation)

        # Classify based on signals
        treatment_type, confidence = self._aggregate_signals(signals)

        # Extract excerpt containing the citation
        excerpt = self._extract_best_excerpt(text, target_citation, signals)

        return TreatmentAnalysis(
            case_name=citing_case.get("caseName", "Unknown"),
            case_id=str(citing_case.get("id", "")),
            citation=citing_case.get("citation", [""])[0] if citing_case.get("citation") else "",
            treatment_type=treatment_type,
            confidence=confidence,
            signals_found=signals,
            excerpt=excerpt,
            date_filed=citing_case.get("dateFiled"),
        )

    def aggregate_treatments(
        self,
        treatments: list[TreatmentAnalysis],
        target_citation: str,
    ) -> AggregatedTreatment:
        """Aggregate multiple treatment analyses into overall assessment.

        Args:
            treatments: List of individual treatment analyses
            target_citation: The citation being analyzed

        Returns:
            Aggregated treatment assessment
        """
        positive_count = sum(1 for t in treatments if t.treatment_type == TreatmentType.POSITIVE)
        negative_count = sum(1 for t in treatments if t.treatment_type == TreatmentType.NEGATIVE)
        neutral_count = sum(1 for t in treatments if t.treatment_type == TreatmentType.NEUTRAL)
        unknown_count = sum(1 for t in treatments if t.treatment_type == TreatmentType.UNKNOWN)

        # Separate negative and positive treatments
        negative_treatments = [t for t in treatments if t.treatment_type == TreatmentType.NEGATIVE]
        positive_treatments = [t for t in treatments if t.treatment_type == TreatmentType.POSITIVE]

        # Determine if case is still good law
        # Any high-confidence negative treatment is a red flag
        critical_negative = any(
            t.confidence >= 0.8 and t.treatment_type == TreatmentType.NEGATIVE
            for t in treatments
        )

        is_good_law = not critical_negative

        # Calculate overall confidence
        if critical_negative:
            # High confidence it's NOT good law if we found strong negative signals
            confidence = max(t.confidence for t in negative_treatments)
        elif negative_count > 0:
            # Some negative treatment but not critical
            confidence = 0.6 - (negative_count * 0.1)
        elif positive_count > negative_count * 2:
            # Strong positive treatment
            confidence = 0.8 + min(0.15, positive_count * 0.03)
        else:
            # Mostly neutral/unknown
            confidence = 0.7

        # Generate summary
        summary = self._generate_summary(
            positive_count,
            negative_count,
            neutral_count,
            is_good_law,
            negative_treatments,
        )

        return AggregatedTreatment(
            citation=target_citation,
            is_good_law=is_good_law,
            confidence=min(confidence, 0.95),  # Cap at 95%
            total_citing_cases=len(treatments),
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            unknown_count=unknown_count,
            negative_treatments=negative_treatments,
            positive_treatments=positive_treatments,
            summary=summary,
        )

    def _extract_citation_contexts(
        self,
        text: str,
        citation: str,
        window: int = 400,  # Increased from 200 to catch more context
    ) -> list[tuple[str, int]]:
        """Extract context windows around mentions of the citation.

        Args:
            text: Full text to search
            citation: Citation to find
            window: Characters before/after to include

        Returns:
            List of (context, position) tuples
        """
        contexts = []

        # Try multiple citation patterns to find all mentions
        # Pattern 1: Direct citation (e.g., "410 U.S. 113")
        citation_pattern = re.escape(citation).replace(r"\ ", r"\s+")
        patterns_to_try = [
            re.compile(citation_pattern, re.IGNORECASE),
        ]

        # Pattern 2: If citation is "XXX U.S. YYY", also try case name
        # (e.g., for "410 U.S. 113", also search for "Roe v. Wade")
        # This helps when signals are near case name but before citation
        us_cite_match = re.match(r"(\d+)\s+U\.?S\.?\s+(\d+)", citation, re.IGNORECASE)
        if us_cite_match:
            # Add pattern for common case names associated with this citation
            well_known_cases = {
                "410 U.S. 113": "Roe v. Wade",
                "539 U.S. 558": "Lawrence v. Texas",
                "505 U.S. 833": "Planned Parenthood v. Casey",
            }
            if citation in well_known_cases:
                case_name = well_known_cases[citation]
                patterns_to_try.append(
                    re.compile(re.escape(case_name).replace(r"\ ", r"\s+"), re.IGNORECASE)
                )

        for pattern in patterns_to_try:
            for match in pattern.finditer(text):
                start = max(0, match.start() - window)
                end = min(len(text), match.end() + window)
                context = text[start:end]
                contexts.append((context, match.start()))

        return contexts if contexts else [(text[:500], 0)]  # Fallback to beginning

    def _aggregate_signals(
        self,
        signals: list[TreatmentSignal],
    ) -> tuple[TreatmentType, float]:
        """Aggregate signals into overall treatment type and confidence.

        Args:
            signals: List of treatment signals

        Returns:
            Tuple of (treatment_type, confidence)
        """
        if not signals:
            return TreatmentType.NEUTRAL, 0.5

        negative_signals = [s for s in signals if s.treatment_type == TreatmentType.NEGATIVE]
        positive_signals = [s for s in signals if s.treatment_type == TreatmentType.POSITIVE]

        # Negative signals take precedence (conservative approach)
        if negative_signals:
            # Get the strongest negative signal
            strongest = max(
                negative_signals,
                key=lambda s: self._get_signal_weight(s.signal, TreatmentType.NEGATIVE),
            )
            weight = self._get_signal_weight(strongest.signal, TreatmentType.NEGATIVE)
            return TreatmentType.NEGATIVE, weight

        elif positive_signals:
            strongest = max(
                positive_signals,
                key=lambda s: self._get_signal_weight(s.signal, TreatmentType.POSITIVE),
            )
            weight = self._get_signal_weight(strongest.signal, TreatmentType.POSITIVE)
            return TreatmentType.POSITIVE, weight

        return TreatmentType.NEUTRAL, 0.5

    def _get_signal_weight(self, signal: str, treatment_type: TreatmentType) -> float:
        """Get the weight for a signal.

        Args:
            signal: Signal text
            treatment_type: Type of treatment

        Returns:
            Weight between 0 and 1
        """
        signals_dict = (
            NEGATIVE_SIGNALS if treatment_type == TreatmentType.NEGATIVE else POSITIVE_SIGNALS
        )

        for pattern_text, (sig, weight) in signals_dict.items():
            if sig == signal:
                return weight

        return 0.5

    def _extract_best_excerpt(
        self,
        text: str,
        citation: str,
        signals: list[TreatmentSignal],
    ) -> str:
        """Extract the most relevant excerpt showing treatment.

        Args:
            text: Full text
            citation: Citation to find
            signals: Treatment signals found

        Returns:
            Most relevant excerpt (max 300 chars)
        """
        if signals:
            # Use context from strongest signal
            best_signal = max(
                signals,
                key=lambda s: self._get_signal_weight(s.signal, s.treatment_type),
            )
            return best_signal.context

        # Fallback: extract around citation
        contexts = self._extract_citation_contexts(text, citation, window=150)
        return contexts[0][0] if contexts else text[:300]

    def _generate_summary(
        self,
        positive_count: int,
        negative_count: int,
        neutral_count: int,
        is_good_law: bool,
        negative_treatments: list[TreatmentAnalysis],
    ) -> str:
        """Generate human-readable summary of treatment analysis.

        Args:
            positive_count: Number of positive treatments
            negative_count: Number of negative treatments
            neutral_count: Number of neutral treatments
            is_good_law: Whether case is still good law
            negative_treatments: List of negative treatment analyses

        Returns:
            Summary string
        """
        if not is_good_law:
            signals = ", ".join(
                set(s.signal for t in negative_treatments for s in t.signals_found[:2])
            )
            return (
                f"⚠️  Case may not be good law. Found {negative_count} negative treatment(s) "
                f"including: {signals}. Recommend manual review."
            )

        if negative_count > 0:
            return (
                f"⚡ Case appears to be good law but has {negative_count} negative treatment(s). "
                f"Also {positive_count} positive, {neutral_count} neutral citations. Review recommended."
            )

        if positive_count > 5:
            return (
                f"✓ Case appears to be good law with strong positive treatment "
                f"({positive_count} positive citations)."
            )

        return (
            f"Case cited {positive_count + negative_count + neutral_count} times "
            f"with no significant negative treatment."
        )
from app.types import CourtListenerCase
