"""Integration tests for complete research workflows.

Tests end-to-end research pipelines combining multiple components.
"""

import pytest

from app.analysis.citation_network import CitationNetworkBuilder
from app.analysis.quote_matcher import QuoteMatcher
from app.analysis.treatment_classifier import TreatmentClassifier, TreatmentType


@pytest.fixture
def real_case_data():
    """Fixture with realistic legal research workflow data."""
    root_case = {
        "caseName": "Roe v. Wade",
        "citation": ["410 U.S. 113"],
        "dateFiled": "1973-01-22",
        "court": "scotus",
        "cluster_id": 100,
        "opinions": [{"id": 1, "snippet": "The right to privacy has been recognized in Supreme Court precedent."}],
    }

    citing_cases = [
        {
            "caseName": "Planned Parenthood v. Casey",
            "citation": ["505 U.S. 833"],
            "dateFiled": "1992-06-29",
            "court": "scotus",
            "cluster_id": 200,
            "opinions": [{
                "id": 2,
                "snippet": "We reaffirm the essential holding of Roe v. Wade."
            }],
        },
        {
            "caseName": "Dobbs v. Jackson Women's Health Organization",
            "citation": ["597 U.S. 215"],
            "dateFiled": "2022-06-24",
            "court": "scotus",
            "cluster_id": 300,
            "opinions": [{
                "id": 3,
                "snippet": "Roe v. Wade was wrongly decided and is overruled."
            }],
        },
    ]

    return {
        "root_case": root_case,
        "citing_cases": citing_cases,
        "full_texts": {
            "100": "The right to privacy has been recognized in Supreme Court precedent from the beginning of this Court's adjudication of rights grounded in the concept of personal liberty.",
            "200": "We reaffirm the essential holding of Roe v. Wade. The ability of women to participate equally in the economic and social life of the Nation has been facilitated by their ability to control their reproductive lives.",
            "300": "Roe v. Wade was wrongly decided and is overruled. The Constitution does not confer a right to abortion.",
        }
    }


@pytest.mark.integration
def test_full_research_pipeline_real_api(real_case_data, mock_client):
    """Test complete research pipeline using real case data."""
    # Configure mock to return our real case data
    mock_client.lookup_citation.return_value = real_case_data["root_case"]
    mock_client.find_citing_cases.return_value = {
        "results": real_case_data["citing_cases"],
        "warnings": [],
        "failed_requests": [],
        "incomplete_data": False,
        "confidence": 1.0,
    }

    # Phase 1: Build citation network
    network_builder = CitationNetworkBuilder(max_depth=2, max_nodes=100)
    network = network_builder.build_network(
        real_case_data["root_case"],
        real_case_data["citing_cases"],
    )

    # Validate network structure
    assert network.root_citation == "410 U.S. 113"
    assert len(network.nodes) == 3
    assert len(network.edges) == 2

    # Phase 2: Classify treatments
    classifier = TreatmentClassifier()
    treatments = []

    for citing_case in real_case_data["citing_cases"]:
        cluster_id = citing_case.get("cluster_id")
        full_text = real_case_data["full_texts"].get(str(cluster_id), "")

        analysis = classifier.classify_treatment(
            citing_case,
            network.root_citation,
            full_text=full_text,
        )
        treatments.append(analysis)

    # Validate treatments
    assert len(treatments) == 2
    # Casey should be positive (reaffirm)
    assert treatments[0].treatment_type == TreatmentType.POSITIVE
    # Dobbs should be negative (overruled)
    assert treatments[1].treatment_type == TreatmentType.NEGATIVE

    # Phase 3: Aggregate treatment
    agg = classifier.aggregate_treatments(treatments, network.root_citation)

    # Validate aggregation
    assert agg.positive_count == 1
    assert agg.negative_count == 1
    assert agg.is_good_law is False  # High-confidence negative overrides


@pytest.mark.integration
def test_quote_verification_real_cases(real_case_data):
    """Test quote verification across multiple cases."""
    matcher = QuoteMatcher()

    quotes_to_verify = [
        {
            "quote": "The right to privacy has been recognized",
            "source": real_case_data["full_texts"]["100"],
            "citation": "410 U.S. 113",
        },
        {
            "quote": "We reaffirm the essential holding of Roe v. Wade",
            "source": real_case_data["full_texts"]["200"],
            "citation": "505 U.S. 833",
        },
        {
            "quote": "Roe v. Wade was wrongly decided and is overruled",
            "source": real_case_data["full_texts"]["300"],
            "citation": "597 U.S. 215",
        },
    ]

    results = []
    for quote_data in quotes_to_verify:
        result = matcher.verify_quote(
            quote_data["quote"],
            quote_data["source"],
            quote_data["citation"],
        )
        results.append(result)

    # Validate all quotes are found
    assert all(r.found for r in results), "All quotes should be found in their sources"

    # Check similarity scores
    assert results[0].similarity >= 0.8
    assert results[1].similarity >= 0.8
    assert results[2].similarity >= 0.8


@pytest.mark.integration
def test_citation_network_real_data(real_case_data):
    """Test complete citation network operations with real data."""
    builder = CitationNetworkBuilder(max_depth=2, max_nodes=50)

    # Build network with treatments
    treatments_data = [
        {
            "citing_case": {"citation": ["505 U.S. 833"]},
            "treatment": "affirmed",
            "confidence": 0.95,
            "excerpt": "We reaffirm the essential holding",
        },
        {
            "citing_case": {"citation": ["597 U.S. 215"]},
            "treatment": "overruled",
            "confidence": 1.0,
            "excerpt": "Roe was wrongly decided",
        },
    ]

    network = builder.build_network(
        real_case_data["root_case"],
        real_case_data["citing_cases"],
        treatments_data,
    )

    # Get statistics
    stats = builder.get_network_statistics(network)

    assert stats["total_nodes"] == 3
    assert stats["total_edges"] == 2
    assert stats["max_depth"] == 1
    assert stats["treatment_distribution"]["affirmed"] == 1
    assert stats["treatment_distribution"]["overruled"] == 1
    assert stats["root_citation_count"] == 2

    # Test filtering by treatment
    affirmed_network = builder.filter_network(network, treatments=["affirmed"])
    assert len(affirmed_network.edges) == 1
    assert affirmed_network.edges[0].treatment == "affirmed"
    assert "505 U.S. 833" in affirmed_network.nodes

    overruled_network = builder.filter_network(network, treatments=["overruled"])
    assert len(overruled_network.edges) == 1
    assert overruled_network.edges[0].treatment == "overruled"

    # Test filtering by confidence
    high_confidence = builder.filter_network(network, min_confidence=0.95)
    assert len(high_confidence.edges) == 2  # Both have confidence >= 0.95

    # Test filtering by date
    recent = builder.filter_network(network, date_after="2000-01-01")
    assert len(recent.edges) == 2  # All cases after 1973


@pytest.mark.integration
def test_multi_step_research_workflow(real_case_data, mock_client):
    """Test a realistic multi-step research workflow."""
    # Step 1: Get root case
    root_case = real_case_data["root_case"]
    assert root_case["caseName"] == "Roe v. Wade"

    # Step 2: Find citing cases (mocked)
    mock_client.find_citing_cases.return_value = {
        "results": real_case_data["citing_cases"],
        "warnings": [],
        "failed_requests": [],
        "incomplete_data": False,
        "confidence": 1.0,
    }

    # Step 3: Build network
    builder = CitationNetworkBuilder()
    network = builder.build_network(root_case, real_case_data["citing_cases"])

    # Step 4: Classify treatments
    classifier = TreatmentClassifier()
    treatments = []

    for citing_case in real_case_data["citing_cases"]:
        cluster_id = citing_case.get("cluster_id")
        full_text = real_case_data["full_texts"].get(str(cluster_id), "")

        analysis = classifier.classify_treatment(
            citing_case,
            "410 U.S. 113",
            full_text=full_text,
        )
        treatments.append(analysis)

    # Step 5: Aggregate results
    agg = classifier.aggregate_treatments(treatments, "410 U.S. 113")

    # Step 6: Verify key quotes
    matcher = QuoteMatcher()
    quote_result = matcher.verify_quote(
        "We reaffirm the essential holding of Roe v. Wade",
        real_case_data["full_texts"]["200"],
        "505 U.S. 833",
    )

    # Validate complete workflow
    assert network.root_citation == "410 U.S. 113"
    assert agg.is_good_law is False
    assert agg.total_citing_cases == 2
    assert quote_result.found
    assert quote_result.similarity >= 0.8
