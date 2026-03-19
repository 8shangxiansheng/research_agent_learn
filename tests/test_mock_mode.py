import asyncio

import app.services.agent as agent_module
from app.services.agent import MockAcademicAgent
from app.services.tools import search_arxiv_papers, search_crossref_records


def test_get_agent_returns_mock_agent_when_mock_mode_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ACADEMIC_QA_MOCK_MODE", "1")
    agent_module._agent_instance = None

    agent = agent_module.get_agent()

    assert isinstance(agent, MockAcademicAgent)
    agent_module._agent_instance = None


def test_mock_agent_returns_deterministic_research_response() -> None:
    agent = MockAcademicAgent()

    response = asyncio.run(
        agent.ainvoke(
            "Research question: graph neural networks\n"
            "Sources:\n"
            "[S1] Mock evidence for graph neural networks\n"
            "[S2] Comparative mock study on graph neural networks"
        )
    )

    assert "Graph Neural Networks" in response
    assert "[S1]" in response
    assert "[S2]" in response


def test_search_arxiv_papers_returns_mock_results_in_mock_mode(monkeypatch) -> None:
    monkeypatch.setenv("ACADEMIC_QA_MOCK_MODE", "1")

    sources = search_arxiv_papers("graph neural networks", max_results=2)

    assert len(sources) == 2
    assert sources[0]["title"] == "Mock evidence for graph neural networks"
    assert sources[0]["citation_text"].startswith("Mock Author, Test Researcher")
    assert sources[1]["title"] == "Comparative mock study on graph neural networks"


def test_search_crossref_records_returns_mock_results_in_mock_mode(monkeypatch) -> None:
    monkeypatch.setenv("ACADEMIC_QA_MOCK_MODE", "1")

    sources = search_crossref_records("graph neural networks", max_results=2)

    assert len(sources) == 2
    assert sources[0]["source_type"] == "crossref"
    assert sources[0]["title"] == "Crossref metadata for graph neural networks"
    assert sources[0]["doi"] == "10.5555/mock-crossref.1"
    assert sources[1]["title"] == "Crossref venue overview for graph neural networks"
