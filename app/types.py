"""Shared TypedDict definitions for structured data types used across the app."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class CourtListenerOpinion(TypedDict, total=False):
    """Opinion entry returned by CourtListener APIs."""

    id: int
    snippet: str
    plain_text: str
    html: str
    html_lawbox: str
    html_columbia: str
    html_anon_2020: str


class CourtListenerCase(TypedDict, total=False):
    """Case metadata as returned by CourtListener search endpoints."""

    id: int
    caseName: str
    citation: list[str]
    dateFiled: str | None
    court: str | None
    syllabus: str
    opinions: list[CourtListenerOpinion]
    plain_text: str
    snippet: str
    text: str
    absolute_url: str


class TreatmentWarning(TypedDict, total=False):
    """Details about a potential negative treatment signal."""

    signal: str
    case_name: str
    citation: str
    date_filed: str | None
    excerpt: str


class TreatmentResult(TypedDict, total=False):
    """Aggregated treatment analysis result."""

    citation: str
    case_name: str | None
    is_good_law: bool
    confidence: float
    summary: str
    total_citing_cases: int
    positive_count: int
    negative_count: int
    neutral_count: int
    unknown_count: int
    warnings: list[str | TreatmentWarning]
    failed_requests: list[dict[str, object]]
    incomplete_data: bool
    recommendation: str
    error: NotRequired[str]


class QuoteMatch(TypedDict, total=False):
    """Represents a single located quote match."""

    position: int
    matched_text: str
    context_before: str
    context_after: str
    differences: list[str]


class QuoteGrounding(TypedDict, total=False):
    """Grounding information for quote alignment."""

    source_span: dict[str, int]
    opinion_section_hint: dict[str, object] | None
    alignment: dict[str, object]


class QuoteVerificationResult(TypedDict, total=False):
    """Result object returned by quote verification tools."""

    citation: str
    case_name: str | None
    quote: str
    found: bool
    exact_match: bool
    similarity: float
    matches_found: int
    warnings: list[str]
    recommendation: str
    best_match: QuoteMatch
    all_match_positions: list[int]
    grounding: QuoteGrounding
    error: str
    error_code: str
    pinpoint_provided: str
    pinpoint_note: str


class CitationNetworkNode(TypedDict, total=False):
    """Node representation within a citation network."""

    citation: str
    case_name: str | None
    date_filed: str | None
    court: str | None
    cluster_id: str | None
    opinion_ids: list[int] | None
    metadata: dict[str, object] | None


class CitationNetworkEdge(TypedDict, total=False):
    """Edge representation within a citation network."""

    from_citation: str
    to_citation: str
    depth: int
    treatment: str | None
    confidence: float | None
    excerpt: str | None


class CitationNetworkStatistics(TypedDict, total=False):
    """Aggregated statistics about a citation network."""

    total_nodes: int
    total_edges: int
    message: str
    treatment_distribution: dict[str, int]
    filters_applied: dict[str, object]


class CitationNetworkResult(TypedDict, total=False):
    """Primary structure returned by citation network builders."""

    root_citation: str
    root_case_name: str | None
    nodes: list[CitationNetworkNode]
    edges: list[CitationNetworkEdge]
    statistics: CitationNetworkStatistics
    warnings: NotRequired[list[str]]
    failed_requests: NotRequired[list[dict[str, object]]]
    incomplete_data: NotRequired[bool]
    error: NotRequired[str]
