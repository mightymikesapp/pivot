"""Tests for citation network analysis."""

import pytest

from app.analysis.citation_network import (
    CitationNetwork,
    CitationNetworkBuilder,
)


@pytest.fixture
def sample_cases():
    return {
        "root": {
            "citation": ["410 U.S. 113"],
            "caseName": "Roe v. Wade",
            "dateFiled": "1973-01-22",
            "court": "scotus",
            "cluster_id": 100,
            "opinions": [{"id": 1}],
            "status": "Precedential",
            "precedentialStatus": "Published",
            "judge": "Blackmun"
        },
        "citing1": {
            "citation": ["505 U.S. 833"],
            "caseName": "Planned Parenthood v. Casey",
            "dateFiled": "1992-06-29",
            "court": "scotus",
            "cluster_id": 200,
            "opinions": [{"id": 2}]
        },
        "citing2": {
            "citation": ["597 U.S. 215"],
            "caseName": "Dobbs v. Jackson",
            "dateFiled": "2022-06-24",
            "court": "scotus",
            "cluster_id": 300,
            "opinions": [{"id": 3}]
        }
    }

@pytest.fixture
def sample_treatments():
    return [
        {
            "citing_case": {
                "citation": ["505 U.S. 833"],
            },
            "treatment": "affirmed",
            "confidence": 0.8,
            "excerpt": "Affirmed in part"
        },
        {
            "citing_case": {
                "citation": ["597 U.S. 215"],
            },
            "treatment": "overruled",
            "confidence": 0.95,
            "excerpt": "Overruled"
        }
    ]

def test_builder_initialization():
    builder = CitationNetworkBuilder(max_depth=3, max_nodes=50)
    assert builder.max_depth == 3
    assert builder.max_nodes == 50

def test_build_network(sample_cases, sample_treatments):
    builder = CitationNetworkBuilder()

    root_case = sample_cases["root"]
    citing_cases = [sample_cases["citing1"], sample_cases["citing2"]]

    network = builder.build_network(root_case, citing_cases, sample_treatments)

    assert isinstance(network, CitationNetwork)
    assert network.root_citation == "410 U.S. 113"
    assert len(network.nodes) == 3
    assert len(network.edges) == 2

    # Check nodes
    assert "410 U.S. 113" in network.nodes
    assert "505 U.S. 833" in network.nodes
    assert "597 U.S. 215" in network.nodes

    # Check edges
    edge1 = next(e for e in network.edges if e.from_citation == "505 U.S. 833")
    assert edge1.to_citation == "410 U.S. 113"
    assert edge1.treatment == "affirmed"
    assert edge1.confidence == 0.8

    edge2 = next(e for e in network.edges if e.from_citation == "597 U.S. 215")
    assert edge2.to_citation == "410 U.S. 113"
    assert edge2.treatment == "overruled"

def test_build_network_max_nodes_limit(sample_cases):
    builder = CitationNetworkBuilder(max_nodes=2) # Root + 1 citing

    root_case = sample_cases["root"]
    citing_cases = [sample_cases["citing1"], sample_cases["citing2"]]

    network = builder.build_network(root_case, citing_cases)

    assert len(network.nodes) == 2 # Root + 1 citing case

def test_get_network_statistics(sample_cases, sample_treatments):
    builder = CitationNetworkBuilder()
    network = builder.build_network(
        sample_cases["root"],
        [sample_cases["citing1"], sample_cases["citing2"]],
        sample_treatments
    )

    stats = builder.get_network_statistics(network)

    assert stats["total_nodes"] == 3
    assert stats["total_edges"] == 2
    assert stats["treatment_distribution"]["affirmed"] == 1
    assert stats["treatment_distribution"]["overruled"] == 1
    assert stats["root_citation_count"] == 2

def test_filter_network(sample_cases, sample_treatments):
    builder = CitationNetworkBuilder()
    network = builder.build_network(
        sample_cases["root"],
        [sample_cases["citing1"], sample_cases["citing2"]],
        sample_treatments
    )

    # Filter by treatment
    filtered_overruled = builder.filter_network(network, treatments=["overruled"])
    assert len(filtered_overruled.edges) == 1
    assert filtered_overruled.edges[0].treatment == "overruled"
    assert "597 U.S. 215" in filtered_overruled.nodes
    assert "505 U.S. 833" not in filtered_overruled.nodes

    # Filter by confidence
    filtered_conf = builder.filter_network(network, min_confidence=0.9)
    assert len(filtered_conf.edges) == 1
    assert filtered_conf.edges[0].treatment == "overruled"

    # Filter by date (after 2000)
    filtered_date = builder.filter_network(network, date_after="2000-01-01")
    assert len(filtered_date.edges) == 1
    assert filtered_date.edges[0].from_citation == "597 U.S. 215"

def test_extract_citation_edge_cases():
    builder = CitationNetworkBuilder()

    # String citation
    case1 = {"citation": "123 U.S. 456"}
    assert builder._extract_citation(case1) == "123 U.S. 456"

    # List citation
    case2 = {"citation": ["123 U.S. 456", "Other Citation"]}
    assert builder._extract_citation(case2) == "123 U.S. 456"

    # No citation, fallback to cluster_id
    case3 = {"cluster_id": 999}
    assert builder._extract_citation(case3) == "999"
