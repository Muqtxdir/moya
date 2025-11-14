"""
Research Orchestrator for MOYA for Research.

Coordinates the multi-agent research paper analysis workflow.
This is a simple Python class (not a MOYA Orchestrator) that manages
the sequential execution of Parser, Summarizer, and Synthesis agents.
"""

import json
from typing import List, Dict
from pathlib import Path
from moya_for_research.agents import (
    create_parser_agent,
    create_summarizer_agent,
    create_synthesis_agent,
)
from moya_for_research.tools import PDFTools, DBTools
from moya_for_research.database import get_session
from moya_for_research.models import Paper
from moya_for_research.config import settings
from loguru import logger


class ResearchOrchestrator:
    """
    Coordinates the multi-agent research paper analysis workflow.

    Workflow:
    1. Parse all PDFs (Parser Agent) and store papers in DB
    2. Summarize each paper (Summarizer Agent) and store summaries in DB
    3. Synthesize cross-paper insights (Synthesis Agent) and store synthesis in DB

    This orchestrator follows industry best practices:
    - Clear separation of concerns (each agent has specific responsibility)
    - Sequential execution with error handling
    - Comprehensive logging for observability
    - Graceful error handling (continue processing other papers if one fails)
    """

    def __init__(self):
        """Initialize all agents."""
        logger.info("Initializing Research Orchestrator")

        self.parser_agent = create_parser_agent()
        self.summarizer_agent = create_summarizer_agent()
        self.synthesis_agent = create_synthesis_agent()

        logger.info("All agents initialized successfully")

    def _write_paper_outputs(self, paper_id: int, paper_data: Dict, summary_data: Dict):
        """Write individual paper outputs to data/paper_{id}/ directory."""
        try:
            paper_dir = settings.DATA_DIR / f"paper_{paper_id}"
            paper_dir.mkdir(parents=True, exist_ok=True)

            # Write metadata
            metadata_file = paper_dir / "metadata.json"
            metadata = {
                "paper_id": paper_id,
                "title": paper_data.get("title", ""),
                "authors": paper_data.get("authors", ""),
                "year": paper_data.get("year", ""),
                "abstract": paper_data.get("abstract", ""),
                "file_name": paper_data.get("file_name", ""),
                "page_count": paper_data.get("page_count", 0),
            }
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            logger.info(f"Wrote metadata to {metadata_file}")

            # Write summary
            summary_file = paper_dir / "summary.json"
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Wrote summary to {summary_file}")

        except Exception as e:
            logger.error(f"Failed to write outputs for paper {paper_id}: {str(e)}")

    def _write_synthesis_outputs(self, synthesis_data: Dict, mini_survey: str):
        """Write synthesis and mini-survey to data/ root directory."""
        try:
            # Write synthesis.json
            synthesis_file = settings.DATA_DIR / "synthesis.json"
            with open(synthesis_file, "w", encoding="utf-8") as f:
                json.dump(synthesis_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Wrote synthesis to {synthesis_file}")

            # Write mini_survey.md
            survey_file = settings.DATA_DIR / "mini_survey.md"
            with open(survey_file, "w", encoding="utf-8") as f:
                f.write(mini_survey)
            logger.info(f"Wrote mini-survey to {survey_file}")

        except Exception as e:
            logger.error(f"Failed to write synthesis outputs: {str(e)}")

    def _parse_summary_response(self, response: str) -> Dict[str, str]:
        """Parse structured summary from LLM response."""
        parts = {}
        current_key = None
        current_text = []

        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("SUMMARY:"):
                current_key = "summary"
                current_text = [line.replace("SUMMARY:", "").strip()]
            elif line.startswith("KEY_FINDINGS:"):
                if current_key and current_text:
                    parts[current_key] = " ".join(current_text)
                current_key = "key_findings"
                current_text = [line.replace("KEY_FINDINGS:", "").strip()]
            elif line.startswith("METHODOLOGY:"):
                if current_key and current_text:
                    parts[current_key] = " ".join(current_text)
                current_key = "methodology"
                current_text = [line.replace("METHODOLOGY:", "").strip()]
            elif line.startswith("CONTRIBUTIONS:"):
                if current_key and current_text:
                    parts[current_key] = " ".join(current_text)
                current_key = "contributions"
                current_text = [line.replace("CONTRIBUTIONS:", "").strip()]
            elif line.startswith("LIMITATIONS:"):
                if current_key and current_text:
                    parts[current_key] = " ".join(current_text)
                current_key = "limitations"
                current_text = [line.replace("LIMITATIONS:", "").strip()]
            elif line and current_key:
                current_text.append(line)

        if current_key and current_text:
            parts[current_key] = " ".join(current_text)

        return parts

    def _parse_synthesis_response(self, response: str) -> Dict:
        """Parse structured synthesis from LLM response."""
        parts = {"synthesis": "", "themes": [], "gaps": [], "directions": []}
        current_section = None
        current_text = []

        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("SYNTHESIS:"):
                current_section = "synthesis"
                current_text = [line.replace("SYNTHESIS:", "").strip()]
            elif line.startswith("THEMES:"):
                if current_section == "synthesis" and current_text:
                    parts["synthesis"] = " ".join(current_text)
                current_section = "themes"
                current_text = []
            elif line.startswith("GAPS:"):
                current_section = "gaps"
                current_text = []
            elif line.startswith("DIRECTIONS:"):
                current_section = "directions"
                current_text = []
            elif line and current_section:
                if current_section == "synthesis":
                    current_text.append(line)
                elif line.startswith("-") or line.startswith("*"):
                    item = line.lstrip("-* ").strip()
                    if item:
                        parts[current_section].append(item)

        if current_section == "synthesis" and current_text:
            parts["synthesis"] = " ".join(current_text)

        return parts

    def process_papers(self, pdf_paths: List[str]) -> Dict:
        """
        Main workflow: process multiple research papers end-to-end.

        Steps:
        1. Parse all PDFs using Parser Agent
        2. Summarize each paper using Summarizer Agent
        3. Synthesize cross-paper insights using Synthesis Agent

        Args:
            pdf_paths: List of absolute paths to PDF files

        Returns:
            Dictionary with results from each stage and any errors
        """
        logger.info(f"Starting research paper processing for {len(pdf_paths)} papers")

        results = {
            "parsing": [],
            "summarization": [],
            "synthesis": None,
            "errors": [],
            "paper_ids": [],
        }

        # Stage 1: Parse all PDFs
        logger.info("Stage 1: Parsing PDFs")

        paper_ids = []

        for idx, pdf_path in enumerate(pdf_paths, 1):
            try:
                logger.info(
                    f"Parsing paper {idx}/{len(pdf_paths)}: {Path(pdf_path).name}"
                )

                # Parse PDF directly
                parse_result = PDFTools.parse_pdf(pdf_path)
                if parse_result["status"] != "success":
                    raise Exception(f"PDF parsing failed: {parse_result.get('error')}")

                # Extract metadata directly
                metadata_result = PDFTools.extract_metadata(pdf_path)
                if metadata_result["status"] != "success":
                    raise Exception(
                        f"Metadata extraction failed: {metadata_result.get('error')}"
                    )

                # Store in database directly
                store_result = DBTools.store_paper(
                    title=metadata_result["title"],
                    authors=metadata_result["authors"],
                    abstract=metadata_result["abstract"],
                    year=metadata_result["year"],
                    full_text=parse_result["text"],
                    file_path=pdf_path,
                    file_name=parse_result["file_name"],
                    page_count=parse_result["page_count"],
                )

                if store_result["status"] != "success":
                    raise Exception(
                        f"Database storage failed: {store_result.get('error')}"
                    )

                paper_id = store_result["paper_id"]
                paper_ids.append(paper_id)
                logger.info(f"Paper stored with ID: {paper_id}")

                results["parsing"].append(
                    {
                        "file": Path(pdf_path).name,
                        "path": pdf_path,
                        "paper_id": paper_id,
                        "status": "success",
                    }
                )

            except Exception as e:
                logger.error(f"Error parsing {Path(pdf_path).name}: {str(e)}")
                results["errors"].append(
                    {"stage": "parsing", "file": Path(pdf_path).name, "error": str(e)}
                )

        results["paper_ids"] = paper_ids

        if not paper_ids:
            logger.error("No papers were successfully parsed. Aborting workflow.")
            return results

        logger.info(f"Stage 1 Complete: {len(paper_ids)} papers parsed successfully")

        # Stage 2: Summarize each paper
        logger.info("Stage 2: Summarizing papers")

        for idx, paper_id in enumerate(paper_ids, 1):
            try:
                logger.info(f"Summarizing paper {idx}/{len(paper_ids)}, ID: {paper_id}")

                # Get paper data
                paper_data = DBTools.get_paper(paper_id)
                if paper_data["status"] != "success":
                    raise Exception(
                        f"Failed to retrieve paper: {paper_data.get('error')}"
                    )

                # Ask LLM to generate structured summary
                prompt = f"""Analyze this research paper and provide a structured summary.

Title: {paper_data["title"]}
Authors: {paper_data["authors"]}
Abstract: {paper_data["abstract"]}

Full Text (first 3000 chars):
{paper_data["full_text"][:3000]}

Provide your analysis in this format:
SUMMARY: [2-3 sentence overview]
KEY_FINDINGS: [bullet points of main findings]
METHODOLOGY: [research methods used]
CONTRIBUTIONS: [novel contributions]
LIMITATIONS: [limitations and future work]"""

                response = self.summarizer_agent.handle_message(prompt)
                logger.info(f"Summary generated for paper {paper_id}")

                # Parse the response to extract structured parts
                summary_parts = self._parse_summary_response(response)

                # Store summary in database
                store_result = DBTools.store_summary(
                    paper_id=paper_id,
                    summary_text=summary_parts.get("summary", response[:500]),
                    key_findings=summary_parts.get("key_findings", ""),
                    methodology=summary_parts.get("methodology", ""),
                    contributions=summary_parts.get("contributions", ""),
                    limitations=summary_parts.get("limitations", ""),
                )

                if store_result["status"] != "success":
                    raise Exception(
                        f"Failed to store summary: {store_result.get('error')}"
                    )

                logger.info(f"Summary stored for paper {paper_id}")

                # Write outputs to files
                self._write_paper_outputs(
                    paper_id=paper_id,
                    paper_data=paper_data,
                    summary_data={
                        "paper_id": paper_id,
                        "summary": summary_parts.get("summary", ""),
                        "key_findings": summary_parts.get("key_findings", ""),
                        "methodology": summary_parts.get("methodology", ""),
                        "contributions": summary_parts.get("contributions", ""),
                        "limitations": summary_parts.get("limitations", ""),
                    },
                )

                results["summarization"].append(
                    {"paper_id": paper_id, "status": "success"}
                )

            except Exception as e:
                logger.error(f"Error summarizing paper {paper_id}: {str(e)}")
                results["errors"].append(
                    {"stage": "summarization", "paper_id": paper_id, "error": str(e)}
                )

        logger.info(
            f"Stage 2 Complete: {len(results['summarization'])} papers summarized"
        )

        # Stage 3: Cross-paper synthesis
        logger.info("Stage 3: Synthesizing insights")

        try:
            logger.info(
                "Analyzing all papers and summaries for common themes, gaps, and opportunities"
            )

            # Get all papers
            papers_data = DBTools.get_all_papers()

            if papers_data["count"] == 0:
                raise Exception("No papers found for synthesis")

            # Build context for LLM
            context = "# Research Papers\n\n"
            for paper in papers_data["papers"]:
                context += f"## Paper {paper['id']}: {paper['title']}\n"
                context += f"Authors: {paper['authors']}\n"
                context += f"Abstract: {paper['abstract'][:300]}...\n\n"

            # Ask LLM to generate synthesis
            prompt = f"""{context}

Analyze these {papers_data["count"]} papers and provide a cross-paper synthesis.

Output format:
SYNTHESIS: [500-800 word analysis discussing common themes, comparing approaches, and identifying patterns]
THEMES: [List 3-5 common themes, one per line starting with dash]
GAPS: [List 3-5 research gaps, one per line starting with dash]
DIRECTIONS: [List 3-5 future directions, one per line starting with dash]

Be specific and reference papers by their titles."""

            response = self.synthesis_agent.handle_message(prompt)
            logger.info("Synthesis generated")

            # Parse response
            synthesis_parts = self._parse_synthesis_response(response)

            # Generate mini-survey (≤800 words with citations)
            logger.info("Generating mini-survey with inline citations")

            # Build paper references for citations
            paper_refs = []
            for idx, paper_id in enumerate(paper_ids, 1):
                paper = next(p for p in papers_data["papers"] if p["id"] == paper_id)
                paper_refs.append(f"[{idx}] {paper['title']} ({paper['year']})")

            references_text = "\n".join(paper_refs)

            survey_prompt = f"""Generate a concise mini-survey (≤800 words) synthesizing these research papers.

Papers:
{context}

Synthesis Summary:
{synthesis_parts.get("synthesis", "")}

Common Themes: {", ".join(synthesis_parts.get("themes", []))}
Research Gaps: {", ".join(synthesis_parts.get("gaps", []))}

Format:
## Introduction
[2-3 sentences on topic scope and relevance]

## Key Themes
[Discuss main themes with inline citations like [1], [2]]

## Research Gaps and Opportunities
[Identify gaps and future directions]

## Conclusion
[1-2 sentences summarizing the field]

## References
[Will be added automatically]

Use inline citations [1], [2], etc. when referencing specific papers.
Be concise, academic, and under 800 words total."""

            survey_response = self.synthesis_agent.handle_message(survey_prompt)

            # Add references section
            mini_survey = survey_response.strip()
            if "## References" not in mini_survey:
                mini_survey += f"\n\n## References\n{references_text}"

            logger.info(f"Mini-survey generated ({len(mini_survey.split())} words)")

            # Store in database with mini-survey
            store_result = DBTools.store_synthesis(
                synthesis_text=synthesis_parts.get("synthesis", response[:800]),
                common_themes=synthesis_parts.get("themes", []),
                research_gaps=synthesis_parts.get("gaps", []),
                future_directions=synthesis_parts.get("directions", []),
                papers_included=paper_ids,
                mini_survey=mini_survey,
            )

            if store_result["status"] != "success":
                raise Exception(
                    f"Failed to store synthesis: {store_result.get('error')}"
                )

            logger.info("Synthesis and mini-survey stored in database")

            # Write synthesis outputs to files
            self._write_synthesis_outputs(
                synthesis_data={
                    "synthesis_text": synthesis_parts.get("synthesis", ""),
                    "common_themes": synthesis_parts.get("themes", []),
                    "research_gaps": synthesis_parts.get("gaps", []),
                    "future_directions": synthesis_parts.get("directions", []),
                    "papers_included": paper_ids,
                    "paper_count": len(paper_ids),
                },
                mini_survey=mini_survey,
            )

            results["synthesis"] = {"status": "success"}
            logger.info("Stage 3 Complete: Synthesis and mini-survey generated")

        except Exception as e:
            logger.error(f"Error in synthesis: {str(e)}")
            results["errors"].append({"stage": "synthesis", "error": str(e)})

        # Summary
        logger.info("Workflow complete")
        logger.info(f"Papers parsed: {len(results['parsing'])}")
        logger.info(f"Papers summarized: {len(results['summarization'])}")
        logger.info(f"Synthesis generated: {'Yes' if results['synthesis'] else 'No'}")
        logger.info(f"Errors encountered: {len(results['errors'])}")

        return results

    def get_progress(self) -> Dict:
        """
        Get current processing status from database.

        Returns:
            Dictionary with paper count, summary count, synthesis count
        """
        try:
            session = get_session()

            from moya_for_research.models import Summary, Synthesis

            paper_count = session.query(Paper).count()
            summary_count = session.query(Summary).count()
            synthesis_count = session.query(Synthesis).count()

            session.close()

            return {
                "papers_parsed": paper_count,
                "papers_summarized": summary_count,
                "syntheses_generated": synthesis_count,
                "status": "active" if paper_count > 0 else "idle",
            }

        except Exception as e:
            logger.error(f"Error getting progress: {str(e)}")
            return {"error": str(e), "status": "error"}

    def get_results(self) -> Dict:
        """
        Retrieve all results from database.

        Returns:
            Dictionary with papers, summaries, and latest synthesis
        """
        try:
            # Use DBTools directly since agents are now in content-generation mode (no tools)
            papers = DBTools.get_all_papers()
            summaries = DBTools.get_all_summaries()
            synthesis = DBTools.get_latest_synthesis()

            return {
                "papers": papers,
                "summaries": summaries,
                "synthesis": synthesis,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error retrieving results: {str(e)}")
            return {"error": str(e), "status": "error"}
