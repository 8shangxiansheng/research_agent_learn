"""Minimal research workflow orchestration."""
from datetime import UTC, datetime
import re
from typing import Any

from app.services.agent import get_agent
from app.services.tools import merge_research_sources, search_arxiv_papers, search_crossref_records
from app.services.research.document_parser import build_document_source


class ResearchOrchestrator:
    """Run a simple plan -> retrieve -> synthesize -> report workflow."""

    _INLINE_CITATION_PATTERN = re.compile(r"\[\s*(S\d+)\s*\]")
    _BARE_CITATION_PATTERN = re.compile(r"(?<!\[)\b(S\d+)\b(?!\])")
    _STRICT_CITATION_PATTERN = re.compile(r"\[(S\d+)\]")
    _SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")

    def build_phase_statuses(
        self,
        *,
        plan: list[str],
        sources: list[dict[str, Any]],
        answer: str,
    ) -> list[dict[str, str]]:
        """Build a completed phase summary for one research result."""
        planning_detail = f"{len(plan)} planned step{'s' if len(plan) != 1 else ''} prepared"
        retrieval_detail = f"{len(sources)} source{'s' if len(sources) != 1 else ''} gathered"
        evidence_count = len(self.build_evidence_map(answer, sources))
        synthesizing_detail = (
            f"{evidence_count} evidence-linked claim{'s' if evidence_count != 1 else ''} synthesized"
            if evidence_count
            else "Research synthesis completed"
        )
        return [
            {"phase": "planning", "status": "completed", "detail": planning_detail},
            {"phase": "retrieving", "status": "completed", "detail": retrieval_detail},
            {"phase": "synthesizing", "status": "completed", "detail": synthesizing_detail},
            {"phase": "completed", "status": "completed", "detail": "Research brief is ready"},
        ]

    def _build_report_filename(self, query: str) -> str:
        safe = "".join(char.lower() if char.isalnum() else "-" for char in query.strip())
        normalized = "-".join(part for part in safe.split("-") if part)
        return f"research-brief-{normalized or 'summary'}.md"

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

    def _remove_unknown_citations(self, answer: str, available_labels: set[str]) -> str:
        """Drop citation markers that do not map to the current source set."""
        def replace(match: re.Match[str]) -> str:
            label = match.group(1)
            return match.group(0) if label in available_labels else ""

        normalized = self._STRICT_CITATION_PATTERN.sub(replace, answer)
        normalized = re.sub(r"\s{2,}", " ", normalized)
        normalized = re.sub(r"\s+([,.;:])", r"\1", normalized)
        return normalized.strip()

    def _split_claim_segments(self, answer: str) -> list[str]:
        """Split the answer into citation-sized claim segments."""
        blocks = [block.strip() for block in answer.split("\n") if block.strip()]
        segments: list[str] = []
        for block in blocks:
            sentence_like = [part.strip() for part in self._SENTENCE_SPLIT_PATTERN.split(block) if part.strip()]
            segments.extend(sentence_like or [block])
        return segments

    def build_evidence_map(
        self,
        answer: str,
        sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Derive a structured claim-to-source view from the synthesized answer."""
        source_titles = {source["citation_label"]: source["title"] for source in sources}
        evidence_items: list[dict[str, Any]] = []

        for segment in self._split_claim_segments(answer):
            citation_labels = [label for label in self._STRICT_CITATION_PATTERN.findall(segment) if label in source_titles]
            if not citation_labels:
                continue
            claim = self._STRICT_CITATION_PATTERN.sub("", segment)
            claim = re.sub(r"\s{2,}", " ", claim).strip(" ,.;:\n\t")
            if not claim:
                continue
            deduped_labels = list(dict.fromkeys(citation_labels))
            evidence_items.append(
                {
                    "claim": claim,
                    "citation_labels": deduped_labels,
                    "source_titles": [source_titles[label] for label in deduped_labels],
                }
            )

        return evidence_items

    def _build_grounding_mode(self, sources: list[dict[str, Any]]) -> str:
        """Describe how the report was grounded."""
        has_local_document = any(
            source.get("source_type") in {"local_document", "local_pdf"} for source in sources
        )
        has_external_sources = any(
            source.get("source_type") not in {"local_document", "local_pdf"} for source in sources
        )

        if has_local_document and has_external_sources:
            return "Local document + external research sources"
        if has_local_document:
            return "Local document only"
        if has_external_sources:
            return "External research sources only"
        return "No source grounding available"

    def _build_key_takeaway_lines(
        self,
        answer: str,
        evidence_map: list[dict[str, Any]],
    ) -> list[str]:
        """Create a concise report summary section from structured evidence."""
        if evidence_map:
            lines = []
            for item in evidence_map[:5]:
                labels = ", ".join(f"[{label}]" for label in item["citation_labels"])
                lines.append(f"- {item['claim']} {labels}".strip())
            return lines

        first_segment = next(
            (segment for segment in self._split_claim_segments(answer) if segment.strip()),
            answer.strip(),
        )
        if not first_segment:
            return ["- No synthesis available."]
        return [f"- {first_segment.strip()}"]

    def _ensure_claim_level_citations(self, answer: str, sources: list[dict[str, Any]]) -> str:
        """Ensure each substantive claim segment carries at least one valid citation."""
        if not sources:
            return answer.strip()

        fallback_labels = " ".join(
            f"[{source['citation_label']}]" for source in sources[: min(2, len(sources))]
        )
        normalized_segments: list[str] = []
        available_labels = {source["citation_label"] for source in sources}

        for segment in self._split_claim_segments(answer):
            cleaned_segment = self._remove_unknown_citations(segment, available_labels)
            if not cleaned_segment:
                continue
            if self._STRICT_CITATION_PATTERN.search(cleaned_segment):
                normalized_segments.append(cleaned_segment)
                continue
            normalized_segments.append(f"{cleaned_segment} {fallback_labels}".strip())

        return "\n\n".join(normalized_segments).strip()

    def _ensure_source_citations(self, answer: str, sources: list[dict[str, Any]]) -> str:
        if not sources:
            return answer.strip()

        normalized = self._normalize_citation_format(answer).strip()
        normalized = self._ensure_claim_level_citations(normalized, sources)
        available_labels = [source["citation_label"] for source in sources]
        cited_labels = [label for label in available_labels if f"[{label}]" in normalized]
        if cited_labels:
            return normalized

        fallback_labels = ", ".join(f"[{label}]" for label in available_labels[: min(3, len(available_labels))])
        return (
            f"{normalized}\n\n"
            f"Evidence basis: {fallback_labels}."
        ).strip()

    def build_plan(self, query: str, has_document: bool = False) -> list[str]:
        normalized_query = query.strip()
        plan = [
            f"Clarify the research objective for: {normalized_query}",
        ]
        if has_document:
            plan.append("Extract the key claims and evidence from the uploaded local document")
            plan.append(f"Retrieve the most relevant external papers and metadata records for: {normalized_query}")
        else:
            plan.append(f"Retrieve the most relevant arXiv papers and Crossref metadata for: {normalized_query}")
        plan.append("Synthesize the evidence into a concise research summary with source-backed takeaways")
        return plan

    def retrieve_sources(
        self,
        query: str,
        max_sources: int = 3,
        document: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        remaining_sources = max_sources

        if document is not None:
            sources.append(build_document_source(document))
            remaining_sources = max(0, max_sources - 1)

        if remaining_sources > 0:
            arxiv_count = remaining_sources if remaining_sources == 1 else max(1, remaining_sources - 1)
            crossref_count = max(0, remaining_sources - arxiv_count)
            sources.extend(search_arxiv_papers(query=query, max_results=arxiv_count))
            if crossref_count > 0:
                sources.extend(search_crossref_records(query=query, max_results=crossref_count))

        return merge_research_sources(sources)

    async def synthesize_answer(self, query: str, sources: list[dict[str, Any]]) -> str:
        if not sources:
            return "No relevant external sources were found for this research topic."

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

    def build_report(
        self,
        query: str,
        plan: list[str],
        sources: list[dict[str, Any]],
        answer: str,
        generated_at: datetime,
    ) -> str:
        evidence_map = self.build_evidence_map(answer, sources)
        generated_label = generated_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            f"# Research Brief: {query}",
            "",
            "## Report Snapshot",
            "",
            f"- Generated: {generated_label}",
            f"- Research Question: {query}",
            f"- Grounding Mode: {self._build_grounding_mode(sources)}",
            f"- Total Sources: {len(sources)}",
            f"- Evidence-Linked Claims: {len(evidence_map)}",
            "",
            "## Key Takeaways",
            "",
        ]
        lines.extend(self._build_key_takeaway_lines(answer, evidence_map))
        lines.extend([
            "",
            "## Research Plan",
            "",
        ])
        lines.extend(f"{index}. {step}" for index, step in enumerate(plan, start=1))
        lines.extend(["", "## Source Catalogue", ""])

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

        lines.extend(["", "## Evidence Map", ""])
        if not evidence_map:
            lines.append("No structured evidence mapping available.")
        else:
            for item in evidence_map:
                labels = ", ".join(f"[{label}]" for label in item["citation_labels"])
                lines.append(f"- {item['claim']} {labels}".strip())

        lines.extend(["", "## Full Synthesis", "", answer.strip(), ""])
        return "\n".join(lines).strip() + "\n"

    async def run(
        self,
        query: str,
        max_sources: int = 3,
        document: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        generated_at = datetime.now(UTC)
        plan = self.build_plan(query, has_document=document is not None)
        sources = self._annotate_sources(
            self.retrieve_sources(query, max_sources=max_sources, document=document)
        )
        answer = await self.synthesize_answer(query, sources)
        report_markdown = self.build_report(query, plan, sources, answer, generated_at)
        return {
            "query": query,
            "status": "completed",
            "generated_at": generated_at,
            "report_filename": self._build_report_filename(query),
            "plan": plan,
            "phase_statuses": self.build_phase_statuses(plan=plan, sources=sources, answer=answer),
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
