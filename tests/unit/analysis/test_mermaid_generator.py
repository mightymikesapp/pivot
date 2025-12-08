"""Unit tests for low-level Mermaid generator helpers."""

import pytest

from app.analysis.mermaid_generator import MermaidGenerator


def test_sanitize_label_escapes_and_truncates():
    generator = MermaidGenerator()

    sanitized = generator._sanitize_label('Case "Name" [v.] {Example}\nLine', max_length=30)

    assert sanitized == "Case 'Name' (v.) (Example) ..."
    assert generator._sanitize_label("A" * 50, max_length=10) == "AAAAAAA..."


@pytest.mark.parametrize(
    "citation, expected_id",
    [
        ("410 U.S. 113", "case_410_U_S__113"),
        ("Case-Name, Inc.", "Case_Name__Inc_"),
        ("123 Example", "case_123_Example"),
    ],
)
def test_get_node_id_produces_safe_identifiers(citation, expected_id):
    generator = MermaidGenerator()
    assert generator._get_node_id(citation) == expected_id


@pytest.mark.parametrize(
    "treatment, expected_style",
    [
        ("OverRuled", "negative"),
        ("Followed", "positive"),
        ("Limited", "questioned"),
        (None, "neutral"),
        ("mentioned", "neutral"),
    ],
)
def test_get_treatment_style_classification(treatment, expected_style):
    generator = MermaidGenerator()
    assert generator._get_treatment_style(treatment) == expected_style


def test_build_color_palette_preserves_base_and_adds_fallbacks():
    generator = MermaidGenerator()
    base_palette = {"positive": "#111111", "unknown": "#222222"}

    palette = generator._build_color_palette(
        ["positive", "custom1", "Custom2", None], base_palette
    )

    assert palette["positive"] == "#111111"
    assert palette["custom1"] == "#4A90E2"
    assert palette["custom2"] == "#2DBE8D"
    assert palette["unknown"] == "#222222"
