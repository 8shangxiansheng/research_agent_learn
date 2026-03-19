"""
Tools for Academic Q&A Agent.
Provides arXiv and metadata retrieval utilities plus LangChain-compatible tool wrappers.
"""
import json
import os
from datetime import datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

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


def _is_mock_mode_enabled() -> bool:
    return os.getenv("ACADEMIC_QA_MOCK_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


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


def merge_research_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize a mixed source list into a stable, deduplicated order."""
    return _dedupe_and_sort_sources(sources)


def _extract_crossref_date(item: dict[str, Any]) -> str:
    """Build an ISO-like date string from a Crossref message item."""
    for field in ("published-print", "published-online", "created", "issued"):
        date_parts = item.get(field, {}).get("date-parts", [])
        if not date_parts or not date_parts[0]:
            continue
        parts = date_parts[0]
        year = parts[0]
        month = parts[1] if len(parts) > 1 else 1
        day = parts[2] if len(parts) > 2 else 1
        return f"{year:04d}-{month:02d}-{day:02d}T00:00:00Z"
    return "1970-01-01T00:00:00Z"


def _normalize_crossref_item(item: dict[str, Any], *, score: int) -> dict[str, Any]:
    """Convert a Crossref item into the shared research source schema."""
    title = (item.get("title") or ["Untitled record"])[0]
    authors = [
        " ".join(part for part in [author.get("given"), author.get("family")] if part).strip()
        for author in item.get("author", [])
        if author.get("given") or author.get("family")
    ]
    subjects = [subject for subject in item.get("subject", []) if subject]
    doi = item.get("DOI")
    journal_ref = (item.get("container-title") or [None])[0]
    published_at = _extract_crossref_date(item)
    url = item.get("URL") or (f"https://doi.org/{doi}" if doi else item.get("resource", {}).get("primary", {}).get("URL"))
    abstract = (
        item.get("abstract")
        or f"Crossref metadata record for {title}. Journal: {journal_ref or 'Unknown venue'}."
    )

    return {
        "source_id": f"crossref-{doi or abs(hash(title))}",
        "arxiv_id": None,
        "title": title,
        "authors": authors or ["Unknown authors"],
        "abstract": abstract,
        "published_at": published_at,
        "url": url or "https://www.crossref.org/",
        "pdf_url": None,
        "primary_category": subjects[0] if subjects else None,
        "categories": subjects,
        "comment": item.get("publisher"),
        "journal_ref": journal_ref,
        "doi": doi,
        "citation_text": _build_citation(
            title=title,
            authors=authors or ["Unknown authors"],
            published_at=published_at,
            journal_ref=journal_ref,
            doi=doi,
        ),
        "source_type": "crossref",
        "score": score,
    }


def search_crossref_records(query: str, max_results: int = 2) -> list[dict[str, Any]]:
    """Return normalized Crossref metadata records for downstream research flows."""
    if max_results <= 0:
        return []

    if _is_mock_mode_enabled():
        records = [
            {
                "source_id": "mock-crossref-1",
                "arxiv_id": None,
                "title": f"Crossref metadata for {query}",
                "authors": ["Metadata Curator", "Index Maintainer"],
                "abstract": (
                    f"This deterministic Crossref-style metadata record enriches {query} "
                    "with venue and DOI level details for mixed-source tests."
                ),
                "published_at": "2025-12-01T00:00:00Z",
                "url": "https://doi.org/10.5555/mock-crossref.1",
                "pdf_url": None,
                "primary_category": "Metadata",
                "categories": ["Metadata", "Citation Index"],
                "comment": "Crossref mock registry",
                "journal_ref": "Journal of Mock Metadata",
                "doi": "10.5555/mock-crossref.1",
                "citation_text": _build_citation(
                    title=f"Crossref metadata for {query}",
                    authors=["Metadata Curator", "Index Maintainer"],
                    published_at="2025-12-01T00:00:00Z",
                    journal_ref="Journal of Mock Metadata",
                    doi="10.5555/mock-crossref.1",
                ),
                "source_type": "crossref",
                "score": max(max_results, 1),
            }
        ]
        if max_results > 1:
            records.append(
                {
                    "source_id": "mock-crossref-2",
                    "arxiv_id": None,
                    "title": f"Crossref venue overview for {query}",
                    "authors": ["Index Maintainer"],
                    "abstract": (
                        f"This secondary metadata entry highlights venue-level context related to {query} "
                        "for testing mixed-source ranking."
                    ),
                    "published_at": "2025-08-15T00:00:00Z",
                    "url": "https://doi.org/10.5555/mock-crossref.2",
                    "pdf_url": None,
                    "primary_category": "Bibliography",
                    "categories": ["Bibliography"],
                    "comment": "Crossref mock registry",
                    "journal_ref": "Proceedings of Metadata Systems",
                    "doi": "10.5555/mock-crossref.2",
                    "citation_text": _build_citation(
                        title=f"Crossref venue overview for {query}",
                        authors=["Index Maintainer"],
                        published_at="2025-08-15T00:00:00Z",
                        journal_ref="Proceedings of Metadata Systems",
                        doi="10.5555/mock-crossref.2",
                    ),
                    "source_type": "crossref",
                    "score": max(max_results - 1, 1),
                }
            )
        return merge_research_sources(records[:max_results])

    params = urlencode(
        {
            "query.bibliographic": query,
            "rows": max_results,
            "sort": "relevance",
            "order": "desc",
        }
    )
    request_url = f"https://api.crossref.org/works?{params}"
    try:
        with urlopen(request_url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []

    items = payload.get("message", {}).get("items", [])
    records = [
        _normalize_crossref_item(item, score=max(max_results - index, 1))
        for index, item in enumerate(items)
    ]
    return merge_research_sources(records)


def search_arxiv_papers(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Return normalized arXiv search results for downstream research flows."""
    if _is_mock_mode_enabled():
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

    return merge_research_sources(papers)


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
