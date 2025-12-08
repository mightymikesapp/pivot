"""Tests for treatment classifier."""

import pytest

from app.analysis.treatment_classifier import (
    TreatmentAnalysis,
    TreatmentClassifier,
    TreatmentSignal,
    TreatmentType,
)


@pytest.fixture
def classifier():
    return TreatmentClassifier()

def test_extract_signals_negative(classifier):
    text = "The case was overruled by subsequent decision."
    signals = classifier.extract_signals(text, "citation")

    assert len(signals) > 0
    assert signals[0].treatment_type == TreatmentType.NEGATIVE
    assert signals[0].signal == "overruled"

def test_extract_signals_positive(classifier):
    text = "We followed the reasoning in the cited case."
    signals = classifier.extract_signals(text, "citation")

    assert len(signals) > 0
    assert signals[0].treatment_type == TreatmentType.POSITIVE
    assert signals[0].signal == "followed"

def test_classify_treatment(classifier):
    citing_case = {
        "caseName": "Citing Case",
        "citation": ["200 U.S. 200"],
        "dateFiled": "2020-01-01"
    }
    full_text = "This case was overruled by Smith v. Jones."

    analysis = classifier.classify_treatment(
        citing_case,
        "100 U.S. 100",
        full_text=full_text
    )

    assert analysis.treatment_type == TreatmentType.NEGATIVE
    assert analysis.confidence >= 0.8
    assert "overruled" in analysis.excerpt

def test_classify_treatment_no_text(classifier):
    citing_case = {
        "caseName": "Citing Case",
        "citation": ["200 U.S. 200"],
        "snippet": "Simple snippet"
    }

    analysis = classifier.classify_treatment(citing_case, "100 U.S. 100")

    assert analysis.treatment_type == TreatmentType.NEUTRAL
    assert analysis.confidence == 0.5

def test_should_fetch_full_text(classifier):
    analysis = TreatmentAnalysis(
        case_name="Test", case_id="1", citation="1",
        treatment_type=TreatmentType.NEGATIVE,
        confidence=0.9, signals_found=[], excerpt=""
    )

    assert classifier.should_fetch_full_text(analysis, "always") is True
    assert classifier.should_fetch_full_text(analysis, "never") is False
    assert classifier.should_fetch_full_text(analysis, "negative_only") is True
    assert classifier.should_fetch_full_text(analysis, "smart") is True

    analysis.treatment_type = TreatmentType.POSITIVE
    assert classifier.should_fetch_full_text(analysis, "negative_only") is False

    analysis.treatment_type = TreatmentType.NEUTRAL
    analysis.confidence = 0.5
    assert classifier.should_fetch_full_text(analysis, "smart") is True # Low confidence

def test_aggregate_treatments(classifier):
    treatments = [
        TreatmentAnalysis(
            case_name="Neg", case_id="1", citation="1",
            treatment_type=TreatmentType.NEGATIVE,
            confidence=0.9, signals_found=[
                TreatmentSignal("overruled", TreatmentType.NEGATIVE, 0, "")
            ], excerpt=""
        ),
        TreatmentAnalysis(
            case_name="Pos", case_id="2", citation="2",
            treatment_type=TreatmentType.POSITIVE,
            confidence=0.8, signals_found=[], excerpt=""
        )
    ]

    agg = classifier.aggregate_treatments(treatments, "100 U.S. 100")

    assert agg.is_good_law is False
    assert agg.negative_count == 1
    assert agg.positive_count == 1
    assert "not be good law" in agg.summary

def test_aggregate_treatments_good_law(classifier):
    treatments = [
        TreatmentAnalysis(
            case_name="Pos", case_id="1", citation="1",
            treatment_type=TreatmentType.POSITIVE,
            confidence=0.9, signals_found=[], excerpt=""
        )
    ] * 6

    agg = classifier.aggregate_treatments(treatments, "100 U.S. 100")

    assert agg.is_good_law is True
    assert "strong positive treatment" in agg.summary

def test_extract_citation_contexts(classifier):
    text = "Before 410 U.S. 113 after"
    contexts = classifier._extract_citation_contexts(text, "410 U.S. 113")
    assert len(contexts) == 1
    assert "410 U.S. 113" in contexts[0][0]

    # Test case name matching
    text = "Before Roe v. Wade after"
    contexts = classifier._extract_citation_contexts(text, "410 U.S. 113")
    assert len(contexts) == 1
    assert "Roe v. Wade" in contexts[0][0]


# Edge Case Tests for Treatment Classifier

def test_ambiguous_signals(classifier):
    """Test handling of ambiguous or conflicting signals in text."""
    # Text with both positive and negative signals
    text = """
    The court distinguished this case from the precedent and found
    the reasoning to be solid and well-established. While the
    prior decision was limited to its facts, this court affirmed
    its core principle.
    """

    signals = classifier.extract_signals(text, "410 U.S. 113")

    # Should find both types of signals
    negative_signals = [s for s in signals if s.treatment_type == TreatmentType.NEGATIVE]
    positive_signals = [s for s in signals if s.treatment_type == TreatmentType.POSITIVE]

    assert len(negative_signals) > 0
    assert len(positive_signals) > 0


def test_conflicting_treatments(classifier):
    """Test classification when signals conflict."""
    # Multiple negative and positive treatments
    treatments = [
        TreatmentAnalysis(
            case_name="Case A", case_id="1", citation="1",
            treatment_type=TreatmentType.NEGATIVE,
            confidence=0.95, signals_found=[], excerpt=""
        ),
        TreatmentAnalysis(
            case_name="Case B", case_id="2", citation="2",
            treatment_type=TreatmentType.NEGATIVE,
            confidence=0.85, signals_found=[], excerpt=""
        ),
        TreatmentAnalysis(
            case_name="Case C", case_id="3", citation="3",
            treatment_type=TreatmentType.POSITIVE,
            confidence=0.9, signals_found=[], excerpt=""
        ),
        TreatmentAnalysis(
            case_name="Case D", case_id="4", citation="4",
            treatment_type=TreatmentType.POSITIVE,
            confidence=0.8, signals_found=[], excerpt=""
        ),
    ]

    agg = classifier.aggregate_treatments(treatments, "100 U.S. 100")

    # With high-confidence negative signals, should flag as not good law
    assert agg.is_good_law is False
    assert agg.negative_count == 2
    assert agg.positive_count == 2


def test_signal_attributes_from_contexts(classifier):
    """Ensure signals include expected type, name, and position from contexts."""
    text = (
        "Background discussion. In 410 U.S. 113 the court overruled prior precedent "
        "and later followed that reasoning in subsequent decisions."
    )
    citation_position = text.index("410 U.S. 113")

    signals = classifier.extract_signals(text, "410 U.S. 113")

    overruled = next(s for s in signals if s.signal == "overruled")
    followed = next(s for s in signals if s.signal == "followed")

    assert overruled.treatment_type == TreatmentType.NEGATIVE
    assert overruled.position == citation_position
    assert "overruled" in overruled.context

    assert followed.treatment_type == TreatmentType.POSITIVE
    assert followed.position == citation_position
    assert "followed" in followed.context


def test_overlapping_and_absent_signals(classifier):
    """Handle overlapping positive/negative patterns and missing matches."""
    overlapping_text = (
        "When citing 410 U.S. 113, the panel noted it was not followed in one respect "
        "but ultimately followed its central holding."
    )
    citation_position = overlapping_text.index("410 U.S. 113")

    overlapping_signals = classifier.extract_signals(overlapping_text, "410 U.S. 113")

    assert any(
        s.signal == "not followed"
        and s.treatment_type == TreatmentType.NEGATIVE
        and s.position == citation_position
        for s in overlapping_signals
    )
    assert any(
        s.signal == "followed"
        and s.treatment_type == TreatmentType.POSITIVE
        and s.position == citation_position
        for s in overlapping_signals
    )

    neutral_text = "The discussion of 410 U.S. 113 focused solely on procedural history."
    neutral_signals = classifier.extract_signals(neutral_text, "410 U.S. 113")

    assert neutral_signals == []


def test_confidence_thresholds(classifier):
    """Test confidence threshold handling at boundaries."""
    # Test critical negative threshold (0.8)
    citing_case = {
        "caseName": "Test Case",
        "citation": ["200 U.S. 200"],
    }

    # Exactly at threshold
    analysis_exact = classifier.classify_treatment(
        citing_case,
        "100 U.S. 100",
        full_text="This case was overruled by subsequent decision."
    )
    assert analysis_exact.treatment_type == TreatmentType.NEGATIVE

    # Below threshold
    analysis_below = classifier.classify_treatment(
        citing_case,
        "100 U.S. 100",
        full_text="Distinguished from the prior case."
    )
    # Distinguished is lower weight (0.5)
    assert analysis_below.treatment_type == TreatmentType.NEGATIVE

    # Test aggregation with confidence boundaries
    treatments = [
        TreatmentAnalysis(
            case_name="Case 1", case_id="1", citation="1",
            treatment_type=TreatmentType.NEGATIVE,
            confidence=0.799,  # Just below critical threshold
            signals_found=[], excerpt=""
        ),
    ]

    agg = classifier.aggregate_treatments(treatments, "100 U.S. 100")
    # Single negative below critical threshold should still be good law
    assert agg.is_good_law is True


def test_full_text_strategy_variations(classifier):
    """Test different full text fetching strategies."""
    analysis_positive = TreatmentAnalysis(
        case_name="Test", case_id="1", citation="1",
        treatment_type=TreatmentType.POSITIVE,
        confidence=0.9, signals_found=[], excerpt=""
    )

    analysis_negative = TreatmentAnalysis(
        case_name="Test", case_id="1", citation="1",
        treatment_type=TreatmentType.NEGATIVE,
        confidence=0.9, signals_found=[], excerpt=""
    )

    analysis_ambiguous = TreatmentAnalysis(
        case_name="Test", case_id="1", citation="1",
        treatment_type=TreatmentType.NEUTRAL,
        confidence=0.45, signals_found=[], excerpt=""
    )

    # Test all strategies
    strategies = ["always", "never", "negative_only", "smart"]

    for strategy in strategies:
        # Always strategy
        if strategy == "always":
            assert classifier.should_fetch_full_text(analysis_positive, strategy) is True
            assert classifier.should_fetch_full_text(analysis_negative, strategy) is True
            assert classifier.should_fetch_full_text(analysis_ambiguous, strategy) is True

        # Never strategy
        elif strategy == "never":
            assert classifier.should_fetch_full_text(analysis_positive, strategy) is False
            assert classifier.should_fetch_full_text(analysis_negative, strategy) is False
            assert classifier.should_fetch_full_text(analysis_ambiguous, strategy) is False

        # Negative only strategy
        elif strategy == "negative_only":
            assert classifier.should_fetch_full_text(analysis_positive, strategy) is False
            assert classifier.should_fetch_full_text(analysis_negative, strategy) is True
            assert classifier.should_fetch_full_text(analysis_ambiguous, strategy) is False

        # Smart strategy
        elif strategy == "smart":
            assert classifier.should_fetch_full_text(analysis_positive, strategy) is False
            assert classifier.should_fetch_full_text(analysis_negative, strategy) is True
            assert classifier.should_fetch_full_text(analysis_ambiguous, strategy) is True  # Low confidence


def test_signal_extraction_with_negation(classifier):
    """Test signal extraction with negation patterns."""
    text_with_negation = "The court did NOT follow the precedent."
    signals = classifier.extract_signals(text_with_negation, "410 U.S. 113")

    # Should detect 'not followed'
    assert any("not followed" in s.signal for s in signals)


def test_signal_extraction_weak_signals(classifier):
    """Test extraction of weaker signals."""
    # 'Distinguished' is a weaker negative signal (0.5 weight)
    text = "This case was distinguished from the cited precedent."
    signals = classifier.extract_signals(text, "410 U.S. 113")

    assert len(signals) > 0
    assert any(s.signal == "distinguished" for s in signals)


def test_aggregate_treatments_edge_counts(classifier):
    """Test aggregation with edge case treatment counts."""
    # Single treatment
    single_treatment = [
        TreatmentAnalysis(
            case_name="Case", case_id="1", citation="1",
            treatment_type=TreatmentType.UNKNOWN,
            confidence=0.5, signals_found=[], excerpt=""
        ),
    ]

    agg = classifier.aggregate_treatments(single_treatment, "100 U.S. 100")
    assert agg.total_citing_cases == 1
    assert agg.unknown_count == 1

    # Many neutral treatments
    neutral_treatments = [
        TreatmentAnalysis(
            case_name=f"Case {i}", case_id=str(i), citation=str(i),
            treatment_type=TreatmentType.NEUTRAL,
            confidence=0.5, signals_found=[], excerpt=""
        )
        for i in range(20)
    ]

    agg = classifier.aggregate_treatments(neutral_treatments, "100 U.S. 100")
    assert agg.is_good_law is True
    assert agg.neutral_count == 20
    assert "no significant negative treatment" in agg.summary


def test_excerpt_extraction_with_signals(classifier):
    """Test best excerpt extraction when signals are present."""
    text = """
    The prior decision was overruled. This critical signal appears early.
    Later in the case we discuss related issues. The overruled principle
    was fundamental to the court's reasoning.
    """

    signals = classifier.extract_signals(text, "410 U.S. 113")
    excerpt = classifier._extract_best_excerpt(text, "410 U.S. 113", signals)

    # Should use context from strongest signal (overruled)
    assert len(excerpt) > 0
    assert isinstance(excerpt, str)
    assert len(excerpt) <= 300  # Limit check
