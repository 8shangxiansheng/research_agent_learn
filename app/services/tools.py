"""
Tools for Academic Q&A Agent.
Provides arxiv search tool for academic paper retrieval.
"""
import arxiv
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool


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
        # Create arxiv client
        client = arxiv.Client()

        # Search for papers
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        # Collect results
        results = list(client.results(search))

        if not results:
            return f"No papers found for query: '{query}'"

        # Format results
        formatted_results = []
        for i, paper in enumerate(results, 1):
            authors = ", ".join([author.name for author in paper.authors[:3]])
            if len(paper.authors) > 3:
                authors += " et al."

            formatted_results.append(
                f"Paper {i}:\n"
                f"  Title: {paper.title}\n"
                f"  Authors: {authors}\n"
                f"  Published: {paper.published.strftime('%Y-%m-%d')}\n"
                f"  ArXiv ID: {paper.entry_id}\n"
                f"  URL: {paper.entry_id}\n"
                f"  Abstract: {paper.summary[:500]}{'...' if len(paper.summary) > 500 else ''}\n"
            )

        return "\n".join(formatted_results)

    except Exception as e:
        return f"Error searching arXiv: {str(e)}"


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
