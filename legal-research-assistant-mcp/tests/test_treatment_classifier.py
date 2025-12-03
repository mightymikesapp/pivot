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
