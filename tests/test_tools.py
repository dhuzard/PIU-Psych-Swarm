"""
Tests for automation/tools.py

All external API calls are mocked — these tests do not require API keys.
"""

import pytest
from unittest.mock import patch, MagicMock


def test_search_pubmed_returns_string():
    """search_pubmed should return a string even when the API returns empty results."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = """<?xml version="1.0"?>
    <PubmedArticleSet></PubmedArticleSet>"""

    with patch("requests.get", return_value=mock_response):
        from automation.tools import search_pubmed
        result = search_pubmed.invoke({"query": "test query", "max_results": 3})
        assert isinstance(result, str)


def test_lookup_doi_returns_string():
    """lookup_doi should return a string for any input."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "message": {
            "title": ["Test Paper"],
            "author": [{"given": "Jane", "family": "Smith"}],
            "published-print": {"date-parts": [[2024]]},
            "container-title": ["Test Journal"],
            "DOI": "10.1234/test",
            "abstract": "Test abstract."
        }
    }

    with patch("requests.get", return_value=mock_response):
        from automation.tools import lookup_doi
        result = lookup_doi.invoke({"query": "10.1234/test"})
        assert isinstance(result, str)


def test_append_traceability_matrix_returns_string(tmp_path):
    """append_traceability_matrix should return a string and write to the matrix file."""
    matrix_path = tmp_path / "Knowledge_Traceability_Matrix.md"
    matrix_path.write_text(
        "# Knowledge Traceability Matrix\n\n"
        "| Source | Author/Agent | Claim | Method | Epistemic Tag |\n"
        "|--------|-------------|-------|--------|---------------|\n"
    )

    import os
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    # Write a minimal swarm_config.yml so load_config() works
    (tmp_path / "swarm_config.yml").write_text(
        "swarm:\n  traceability_matrix: './Knowledge_Traceability_Matrix.md'\n"
        "  name: 'test'\n  description: 'test'\n  output_dir: './Drafts'\n"
        "orchestrator:\n  agent: 'O'\n  journalist: 'J'\n"
        "  max_agent_calls: 1\n  max_tool_rounds_per_agent: 1\n"
        "model:\n  provider: 'openai'\n  name: 'gpt-4o'\n"
        "  temperature: 0.2\n  env_key: 'OPENAI_API_KEY'\n"
        "personas: []\ntools: {}\n"
        "reviewer:\n  enabled: false\n  max_revision_loops: 1\n"
        "  banned_words: []\n  required_elements: []\n"
        "  rejection_patterns: []\n  tone: 'neutral'\n"
        "hitl:\n  enabled: false\n  checkpoints: []\n"
        "epistemic_tags: ['[FACT]']\n"
    )

    try:
        from automation.tools import append_traceability_matrix
        result = append_traceability_matrix.invoke({
            "source": "PubMed PMID:12345",
            "agent": "TestAgent",
            "claim": "Test claim",
            "method": "Database search",
            "tag": "[FACT]"
        })
        assert isinstance(result, str)
    finally:
        os.chdir(original_cwd)
