"""Minimal research workflow orchestration."""
from datetime import UTC, datetime
import re
from typing import Any

from app.services.agent import get_agent
from app.services.tools import search_arxiv_papers


class ResearchOrchestrator:
    """Run a simple plan -> retrieve -> synthesize -> report workflow."""

    _INLINE_CITATION_PATTERN = re.compile(r"\[\s*(S\d+)\s*\]")
    _BARE_CITATION_PATTERN = re.compile(r"(?<!\[)\b(S\d+)\b(?!\])")

    def _build_report_filename(self, query: str) -> str:
        safe = "".join(char.lower() if char.isalnum() else "-" for char in query.strip())
        normalized = "-".join(part for part in safe.split("-") if part)
        return f"{normalized or 'research-brief'}.md"

    def _annotate_sources(self, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                **source,
                "citation_label": f"S{index}",
            }
            for index, source in enumerate(sources, start=1)
        ]

    def _normalize_citation_format(self, answer: str) -> str:
        normalized = self._INLINE_CITATION_PATTERN.sub(r"[\1]", answer)
        return self._BARE_CITATION_PATTERN.sub(r"[\1]", normalized)

    def _ensure_source_citations(self, answer: str, sources: list[dict[str, Any]]) -> str:
        if not sources:
            return answer.strip()

        normalized = self._normalize_citation_format(answer).strip()
        available_labels = [source["citation_label"] for source in sources]
        cited_labels = [label for label in available_labels if f"[{label}]" in normalized]
        if cited_labels:
            return normalized

        fallback_labels = ", ".join(f"[{label}]" for label in available_labels[: min(3, len(available_labels))])
        return (
            f"{normalized}\n\n"
            f"Evidence basis: {fallback_labels}."
        ).strip()

    def build_plan(self, query: str) -> list[str]:
        normalized_query = query.strip()
        return [
            f"Clarify the research objective for: {normalized_query}",
            f"Retrieve the most relevant arXiv papers for: {normalized_query}",
            "Synthesize the evidence into a concise research summary with source-backed takeaways",
        ]

    def retrieve_sources(self, query: str, max_sources: int = 3) -> list[dict[str, Any]]:
        return search_arxiv_papers(query=query, max_results=max_sources)

    async def synthesize_answer(self, query: str, sources: list[dict[str, Any]]) -> str:
        if not sources:
            return "No relevant arXiv sources were found for this research topic."

        formatted_sources = "\n\n".join(
            (
                f"[{source['citation_label']}] {source['title']}\n"
                f"Authors: {', '.join(source['authors'][:5])}\n"
                f"Published: {source['published_at'][:10]}\n"
                f"Citation: {source.get('citation_text', 'N/A')}\n"
                f"Abstract: {source['abstract'][:1200]}"
            )
            for source in sources
        )

        prompt = (
            "You are preparing a concise academic research brief.\n"
            "Use the provided sources to answer the research question.\n"
            "Requirements:\n"
            "- Summarize the main findings in plain academic English\n"
            "- Mention uncertainty when evidence is incomplete\n"
            "- Cite claims inline with source markers like [S1] or [S2]\n"
            "- End with a short 'Suggested next reading' sentence\n\n"
            f"Research question: {query}\n\n"
            f"Sources:\n{formatted_sources}"
        )
        answer = await get_agent().ainvoke(prompt)
        return self._ensure_source_citations(answer, sources)

    def build_report(self, query: str, plan: list[str], sources: list[dict[str, Any]], answer: str) -> str:
        lines = [
            f"# Research Brief: {query}",
            "",
            "## Research Plan",
            "",
        ]
        lines.extend(f"{index}. {step}" for index, step in enumerate(plan, start=1))
        lines.extend(["", "## Sources", ""])

        if not sources:
            lines.append("No sources found.")
        else:
            for source in sources:
                authors = ", ".join(source["authors"][:5]) or "Unknown authors"
                lines.extend(
                    [
                        f"### [{source['citation_label']}] {source['title']}",
                        "",
                        f"- Authors: {authors}",
                        f"- Published: {source['published_at'][:10]}",
                        f"- Citation: {source.get('citation_text') or 'N/A'}",
                        f"- Source Type: {source['source_type']}",
                        f"- arXiv ID: {source.get('arxiv_id') or 'N/A'}",
                        f"- Primary Category: {source.get('primary_category') or 'N/A'}",
                        f"- Categories: {', '.join(source.get('categories', [])) or 'N/A'}",
                        f"- Journal Ref: {source.get('journal_ref') or 'N/A'}",
                        f"- DOI: {source.get('doi') or 'N/A'}",
                        f"- URL: {source['url']}",
                        f"- PDF: {source['pdf_url'] or 'N/A'}",
                        "",
                        source["abstract"],
                        "",
                    ]
                )

        lines.extend(["## Synthesis", "", answer.strip(), ""])
        return "\n".join(lines).strip() + "\n"

    async def run(self, query: str, max_sources: int = 3) -> dict[str, Any]:
        plan = self.build_plan(query)
        sources = self._annotate_sources(self.retrieve_sources(query, max_sources=max_sources))
        answer = await self.synthesize_answer(query, sources)
        report_markdown = self.build_report(query, plan, sources, answer)
        return {
            "query": query,
            "status": "completed",
            "generated_at": datetime.now(UTC),
            "report_filename": self._build_report_filename(query),
            "plan": plan,
            "sources": sources,
            "answer": answer,
            "report_markdown": report_markdown,
        }


_research_orchestrator: ResearchOrchestrator | None = None


def get_research_orchestrator() -> ResearchOrchestrator:
    """Return a singleton research orchestrator."""
    global _research_orchestrator
    if _research_orchestrator is None:
        _research_orchestrator = ResearchOrchestrator()
    return _research_orchestrator
