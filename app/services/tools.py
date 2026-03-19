"""
Tools for Academic Q&A Agent.
Provides arXiv retrieval utilities and LangChain-compatible tool wrappers.
"""
import os
from datetime import datetime
from typing import Any

import arxiv
from langchain_core.tools import tool


def _extract_arxiv_id(entry_id: str) -> str:
    """Extract a readable arXiv identifier from an entry URL."""
    return entry_id.rstrip("/").split("/")[-1]


def _build_citation(
    *,
    title: str,
    authors: list[str],
    published_at: str,
    journal_ref: str | None,
    doi: str | None,
) -> str:
    """Build a compact citation string for UI and report rendering."""
    author_text = ", ".join(authors[:3]) if authors else "Unknown authors"
    if len(authors) > 3:
        author_text += ", et al."

    year = published_at[:4] if published_at else "n.d."
    parts = [f"{author_text} ({year}). {title}."]
    if journal_ref:
        parts.append(journal_ref)
    if doi:
        parts.append(f"DOI: {doi}")
    return " ".join(parts)


def _dedupe_and_sort_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate papers and return a stable ranking order."""
    unique_sources: dict[str, dict[str, Any]] = {}

    def published_sort_value(source: dict[str, Any]) -> float:
        published_at = source.get("published_at", "")
        if not published_at:
            return 0.0
        try:
            return datetime.fromisoformat(published_at.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0

    for source in sources:
        dedupe_key = (
            source.get("doi")
            or source.get("arxiv_id")
            or source.get("url")
            or source.get("title", "").strip().lower()
        )
        existing = unique_sources.get(dedupe_key)
        if existing is None:
            unique_sources[dedupe_key] = source
            continue

        existing_score = existing.get("score", 0)
        current_score = source.get("score", 0)
        existing_date = published_sort_value(existing)
        current_date = published_sort_value(source)
        if (current_score, current_date) > (existing_score, existing_date):
            unique_sources[dedupe_key] = source

    return sorted(
        unique_sources.values(),
        key=lambda source: (
            -int(source.get("score", 0)),
            -published_sort_value(source),
            source.get("title", "").lower(),
        ),
    )


def search_arxiv_papers(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Return normalized arXiv search results for downstream research flows."""
    if os.getenv("ACADEMIC_QA_MOCK_MODE", "").strip().lower() in {"1", "true", "yes", "on"}:
        published_at = "2026-03-19T10:00:00+00:00"
        mock_results = [
            {
                "source_id": "mock-arxiv-1",
                "arxiv_id": "2603.19001",
                "title": f"Mock evidence for {query}",
                "authors": ["Mock Author", "Test Researcher"],
                "abstract": (
                    f"This deterministic mock paper summarizes the core evidence for {query}. "
                    "It exists to make browser-based end-to-end tests stable and repeatable."
                ),
                "published_at": published_at,
                "url": "https://example.com/mock-paper-1",
                "pdf_url": "https://example.com/mock-paper-1.pdf",
                "primary_category": "cs.AI",
                "categories": ["cs.AI", "cs.IR"],
                "comment": None,
                "journal_ref": "Mock Testing Workshop 2026",
                "doi": "10.0000/mock.2026.1",
                "citation_text": _build_citation(
                    title=f"Mock evidence for {query}",
                    authors=["Mock Author", "Test Researcher"],
                    published_at=published_at,
                    journal_ref="Mock Testing Workshop 2026",
                    doi="10.0000/mock.2026.1",
                ),
                "source_type": "arxiv",
                "score": max(max_results, 1),
            }
        ]
        if max_results > 1:
            mock_results.append(
                {
                    "source_id": "mock-arxiv-2",
                    "arxiv_id": "2603.19002",
                    "title": f"Comparative mock study on {query}",
                    "authors": ["Regression Bot"],
                    "abstract": (
                        f"This secondary mock paper compares approaches related to {query} "
                        "so research ranking and citation flows can be exercised in tests."
                    ),
                    "published_at": "2026-03-18T10:00:00+00:00",
                    "url": "https://example.com/mock-paper-2",
                    "pdf_url": "https://example.com/mock-paper-2.pdf",
                    "primary_category": "cs.LG",
                    "categories": ["cs.LG"],
                    "comment": None,
                    "journal_ref": None,
                    "doi": None,
                    "citation_text": _build_citation(
                        title=f"Comparative mock study on {query}",
                        authors=["Regression Bot"],
                        published_at="2026-03-18T10:00:00+00:00",
                        journal_ref=None,
                        doi=None,
                    ),
                    "source_type": "arxiv",
                    "score": max(max_results - 1, 1),
                }
            )
        return _dedupe_and_sort_sources(mock_results[:max_results])

    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    papers: list[dict[str, Any]] = []

    for index, paper in enumerate(client.results(search), start=1):
        authors = [author.name for author in paper.authors]
        published_at = paper.published.isoformat()
        arxiv_id = _extract_arxiv_id(paper.entry_id)
        journal_ref = getattr(paper, "journal_ref", None)
        doi = getattr(paper, "doi", None)
        papers.append(
            {
                "source_id": f"arxiv-{index}",
                "arxiv_id": arxiv_id,
                "title": paper.title,
                "authors": authors,
                "abstract": paper.summary,
                "published_at": published_at,
                "url": paper.entry_id,
                "pdf_url": getattr(paper, "pdf_url", None),
                "primary_category": getattr(paper, "primary_category", None),
                "categories": list(getattr(paper, "categories", []) or []),
                "comment": getattr(paper, "comment", None),
                "journal_ref": journal_ref,
                "doi": doi,
                "citation_text": _build_citation(
                    title=paper.title,
                    authors=authors,
                    published_at=published_at,
                    journal_ref=journal_ref,
                    doi=doi,
                ),
                "source_type": "arxiv",
                "score": max(max_results - index + 1, 1),
            }
        )

    return _dedupe_and_sort_sources(papers)


@tool
def arxiv_search(query: str, max_results: int = 5) -> str:
    """
    Search for academic papers on arXiv.

    Args:
        query: Search query for papers
        max_results: Maximum number of results to return (default: 5)

    Returns:
        Formatted string with paper information including title, authors, abstract, and URL
    """
    try:
        results = search_arxiv_papers(query=query, max_results=max_results)
        if not results:
            return f"No papers found for query: '{query}'"

        formatted_results = []
        for i, paper in enumerate(results, 1):
            authors = ", ".join(paper["authors"][:3])
            if len(paper["authors"]) > 3:
                authors += " et al."

            formatted_results.append(
                f"Paper {i}:\n"
                f"  Title: {paper['title']}\n"
                f"  Authors: {authors}\n"
                f"  Published: {paper['published_at'][:10]}\n"
                f"  ArXiv ID: {paper['url']}\n"
                f"  URL: {paper['url']}\n"
                f"  Abstract: {paper['abstract'][:500]}{'...' if len(paper['abstract']) > 500 else ''}\n"
            )

        return "\n".join(formatted_results)

    except Exception as exc:
        return f"Error searching arXiv: {str(exc)}"


class ArxivSearchTool:
    """
    Wrapper class for arxiv search tool.
    Provides a convenient interface for the LangChain tool.
    """

    @staticmethod
    def get_tool():
        """Get the arxiv search tool for LangChain agent."""
        return arxiv_search

    @staticmethod
    def search(query: str, max_results: int = 5) -> str:
        """
        Direct search method without LangChain tool wrapper.

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            Formatted search results
        """
        return arxiv_search.invoke({"query": query, "max_results": max_results})
