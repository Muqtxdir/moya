"""
Analysis Tools for MOYA for Research paper co-pilot.

Provides helper tools for cross-paper analysis and synthesis.
These tools prepare and format data for LLM analysis rather than performing
analysis themselves (which is done by agents).
"""

from typing import List
from loguru import logger


class AnalysisTools:
    """Tools for preparing data for cross-paper analysis."""

    @staticmethod
    def prepare_papers_for_analysis(papers_data: List[dict]) -> dict:
        """
        Prepare a list of papers for analysis by formatting them into a structured format.

        This tool aggregates paper information (title, abstract, summaries) into a format
        that can be easily analyzed by an LLM agent.

        Parameters:
        - papers_data: List of paper dictionaries with 'id', 'title', 'abstract', etc.

        Returns:
        - Dictionary with 'formatted_text', 'paper_count', 'papers_summary'
        """
        try:
            if not papers_data:
                logger.warning("No papers provided for analysis preparation")
                return {
                    "formatted_text": "",
                    "paper_count": 0,
                    "papers_summary": [],
                    "status": "empty",
                }

            formatted_sections = []
            papers_summary = []

            for idx, paper in enumerate(papers_data, 1):
                # Create a formatted section for each paper
                section = f"""
Paper {idx}: {paper.get("title", "Untitled")}
Authors: {paper.get("authors", "Unknown")}
Year: {paper.get("year", "N/A")}
Abstract: {paper.get("abstract", "No abstract")[:500]}...
"""
                formatted_sections.append(section.strip())

                # Create summary entry
                papers_summary.append(
                    {
                        "id": paper.get("id"),
                        "title": paper.get("title", "Untitled"),
                        "year": paper.get("year"),
                    }
                )

            formatted_text = "\n\n---\n\n".join(formatted_sections)

            logger.info(f"Prepared {len(papers_data)} papers for analysis")

            return {
                "formatted_text": formatted_text,
                "paper_count": len(papers_data),
                "papers_summary": papers_summary,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error preparing papers for analysis: {str(e)}")
            return {"error": str(e), "status": "failed"}

    @staticmethod
    def prepare_summaries_for_synthesis(summaries_data: List[dict]) -> dict:
        """
        Prepare paper summaries for cross-paper synthesis.

        Formats summaries with their key findings, methodologies, and contributions
        to facilitate theme identification and gap analysis.

        Parameters:
        - summaries_data: List of summary dictionaries with 'summary_text', 'key_findings', etc.

        Returns:
        - Dictionary with 'formatted_text', 'summary_count', 'status'
        """
        try:
            if not summaries_data:
                logger.warning("No summaries provided for synthesis preparation")
                return {"formatted_text": "", "summary_count": 0, "status": "empty"}

            formatted_sections = []

            for idx, summary in enumerate(summaries_data, 1):
                # Create a formatted section for each summary
                section = f"""
Summary {idx} (Paper ID: {summary.get("paper_id", "N/A")}):

Overview: {summary.get("summary_text", "No summary")[:300]}...

Key Findings: {summary.get("key_findings", "Not specified")}

Methodology: {summary.get("methodology", "Not specified")}

Contributions: {summary.get("contributions", "Not specified")}

Limitations: {summary.get("limitations", "Not specified")}
"""
                formatted_sections.append(section.strip())

            formatted_text = "\n\n" + "=" * 80 + "\n\n".join(formatted_sections)

            logger.info(f"Prepared {len(summaries_data)} summaries for synthesis")

            return {
                "formatted_text": formatted_text,
                "summary_count": len(summaries_data),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error preparing summaries for synthesis: {str(e)}")
            return {"error": str(e), "status": "failed"}

    @staticmethod
    def format_synthesis_output(
        common_themes: List[str], research_gaps: List[str], future_directions: List[str]
    ) -> dict:
        """
        Format synthesis results into a structured output.

        Parameters:
        - common_themes: List of identified themes
        - research_gaps: List of research gaps
        - future_directions: List of future opportunities

        Returns:
        - Dictionary with formatted synthesis text and structured data
        """
        try:
            synthesis_sections = []

            # Common Themes Section
            themes_text = "## Common Themes Across Papers\n\n"
            for idx, theme in enumerate(common_themes, 1):
                themes_text += f"{idx}. {theme}\n"
            synthesis_sections.append(themes_text)

            # Research Gaps Section
            gaps_text = "## Identified Research Gaps\n\n"
            for idx, gap in enumerate(research_gaps, 1):
                gaps_text += f"{idx}. {gap}\n"
            synthesis_sections.append(gaps_text)

            # Future Directions Section
            directions_text = "## Future Research Directions\n\n"
            for idx, direction in enumerate(future_directions, 1):
                directions_text += f"{idx}. {direction}\n"
            synthesis_sections.append(directions_text)

            formatted_synthesis = "\n\n".join(synthesis_sections)

            logger.info("Formatted synthesis output")

            return {
                "formatted_synthesis": formatted_synthesis,
                "common_themes": common_themes,
                "research_gaps": research_gaps,
                "future_directions": future_directions,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error formatting synthesis output: {str(e)}")
            return {"error": str(e), "status": "failed"}

    @staticmethod
    def extract_themes_from_text(synthesis_text: str) -> dict:
        """
        Extract structured themes, gaps, and directions from unstructured synthesis text.

        Uses simple heuristics to identify sections and bullet points.
        The agent should structure its output, but this provides a fallback.

        Parameters:
        - synthesis_text: Unstructured synthesis text from agent

        Returns:
        - Dictionary with extracted 'themes', 'gaps', 'directions'
        """
        try:
            themes = []
            gaps = []
            directions = []

            lines = synthesis_text.split("\n")
            current_section = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Detect section headers
                if "theme" in line.lower() and ("##" in line or "**" in line):
                    current_section = "themes"
                    continue
                elif "gap" in line.lower() and ("##" in line or "**" in line):
                    current_section = "gaps"
                    continue
                elif "future" in line.lower() or "direction" in line.lower():
                    if "##" in line or "**" in line:
                        current_section = "directions"
                        continue

                # Extract bullet points
                if line.startswith(("-", "*", '"', "1.", "2.", "3.", "4.", "5.")):
                    cleaned_line = line.lstrip('-*"123456789. ').strip()
                    if current_section == "themes":
                        themes.append(cleaned_line)
                    elif current_section == "gaps":
                        gaps.append(cleaned_line)
                    elif current_section == "directions":
                        directions.append(cleaned_line)

            logger.info(
                f"Extracted {len(themes)} themes, {len(gaps)} gaps, {len(directions)} directions"
            )

            return {
                "themes": themes,
                "gaps": gaps,
                "directions": directions,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error extracting themes from text: {str(e)}")
            return {
                "error": str(e),
                "status": "failed",
                "themes": [],
                "gaps": [],
                "directions": [],
            }
