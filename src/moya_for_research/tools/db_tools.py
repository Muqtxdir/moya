"""
Database Tools for MOYA for Research paper analysis.

Provides tools for storing and retrieving papers, summaries, and synthesis.
"""

from typing import List, Optional
from moya_for_research.database import get_session
from moya_for_research.models import Paper, Summary, Synthesis
from loguru import logger


class DBTools:
    """Tools for database operations."""

    @staticmethod
    def store_paper(
        title: str,
        authors: str,
        abstract: str,
        full_text: str,
        file_path: str,
        file_name: str,
        page_count: int,
        year: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Store a parsed research paper in the database.

        Parameters:
        - title: Paper title
        - authors: Comma-separated author names
        - abstract: Paper abstract
        - full_text: Complete paper text
        - file_path: Original file path
        - file_name: Original file name
        - page_count: Number of pages in the PDF
        - year: Publication year (optional)
        - metadata: Additional metadata as dictionary (optional)

        Returns:
        - Dictionary with 'paper_id', 'status', 'error' (if any)
        """
        try:
            session = get_session()

            paper = Paper(
                title=title,
                authors=authors,
                abstract=abstract,
                full_text=full_text,
                file_path=file_path,
                file_name=file_name,
                page_count=page_count,
                year=year,
                extra_metadata=metadata or {},
            )

            session.add(paper)
            session.commit()
            session.refresh(paper)

            paper_id = paper.id
            session.close()

            logger.info(f"Stored paper: {title} (ID: {paper_id})")

            return {
                "paper_id": paper_id,
                "status": "success",
                "message": f"Paper '{title}' stored successfully with ID {paper_id}",
            }

        except Exception as e:
            logger.error(f"Error storing paper '{title}': {str(e)}")
            return {"error": str(e), "status": "failed", "title": title}

    @staticmethod
    def get_paper(paper_id: int) -> dict:
        """
        Retrieve a paper by ID from the database.

        Parameters:
        - paper_id: Database ID of the paper

        Returns:
        - Dictionary with paper data or error
        """
        try:
            session = get_session()
            paper = session.query(Paper).filter(Paper.id == paper_id).first()
            session.close()

            if not paper:
                logger.warning(f"Paper {paper_id} not found")
                return {"error": f"Paper {paper_id} not found", "status": "not_found"}

            logger.info(f"Retrieved paper: {paper.title} (ID: {paper_id})")

            return {
                "id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "full_text": paper.full_text,
                "year": paper.year,
                "page_count": paper.page_count,
                "file_name": paper.file_name,
                "created_at": str(paper.created_at),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error retrieving paper {paper_id}: {str(e)}")
            return {"error": str(e), "status": "failed", "paper_id": paper_id}

    @staticmethod
    def get_all_papers() -> dict:
        """
        Retrieve all papers from the database.

        Returns:
        - Dictionary with list of papers and count
        """
        try:
            session = get_session()
            papers = session.query(Paper).all()
            session.close()

            papers_list = []
            for paper in papers:
                papers_list.append(
                    {
                        "id": paper.id,
                        "title": paper.title,
                        "authors": paper.authors,
                        "abstract": paper.abstract,
                        "full_text": paper.full_text,
                        "year": paper.year,
                        "page_count": paper.page_count,
                        "file_name": paper.file_name,
                    }
                )

            logger.info(f"Retrieved {len(papers_list)} papers from database")

            return {
                "papers": papers_list,
                "count": len(papers_list),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error retrieving all papers: {str(e)}")
            return {"error": str(e), "status": "failed", "papers": [], "count": 0}

    @staticmethod
    def store_summary(
        paper_id: int,
        summary_text: str,
        key_findings: Optional[str] = None,
        methodology: Optional[str] = None,
        contributions: Optional[str] = None,
        limitations: Optional[str] = None,
    ) -> dict:
        """
        Store a paper summary in the database.

        Parameters:
        - paper_id: ID of the paper being summarized
        - summary_text: Complete summary text
        - key_findings: Key findings from the paper (optional)
        - methodology: Research methodology description (optional)
        - contributions: Main contributions (optional)
        - limitations: Study limitations (optional)

        Returns:
        - Dictionary with 'summary_id', 'status', 'error' (if any)
        """
        try:
            session = get_session()

            # Verify paper exists
            paper = session.query(Paper).filter(Paper.id == paper_id).first()
            if not paper:
                session.close()
                logger.warning(f"Cannot store summary: Paper {paper_id} not found")
                return {"error": f"Paper {paper_id} not found", "status": "not_found"}

            summary = Summary(
                paper_id=paper_id,
                summary_text=summary_text,
                key_findings=key_findings,
                methodology=methodology,
                contributions=contributions,
                limitations=limitations,
            )

            session.add(summary)
            session.commit()
            session.refresh(summary)

            summary_id = summary.id
            session.close()

            logger.info(
                f"Stored summary for paper {paper_id} (Summary ID: {summary_id})"
            )

            return {
                "summary_id": summary_id,
                "paper_id": paper_id,
                "status": "success",
                "message": f"Summary for paper {paper_id} stored successfully",
            }

        except Exception as e:
            logger.error(f"Error storing summary for paper {paper_id}: {str(e)}")
            return {"error": str(e), "status": "failed", "paper_id": paper_id}

    @staticmethod
    def get_summary(paper_id: int) -> dict:
        """
        Retrieve the summary for a specific paper.

        Parameters:
        - paper_id: ID of the paper

        Returns:
        - Dictionary with summary data or error
        """
        try:
            session = get_session()
            summary = (
                session.query(Summary).filter(Summary.paper_id == paper_id).first()
            )
            session.close()

            if not summary:
                logger.warning(f"No summary found for paper {paper_id}")
                return {
                    "error": f"No summary found for paper {paper_id}",
                    "status": "not_found",
                }

            logger.info(f"Retrieved summary for paper {paper_id}")

            return {
                "id": summary.id,
                "paper_id": summary.paper_id,
                "summary_text": summary.summary_text,
                "key_findings": summary.key_findings,
                "methodology": summary.methodology,
                "contributions": summary.contributions,
                "limitations": summary.limitations,
                "created_at": str(summary.created_at),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error retrieving summary for paper {paper_id}: {str(e)}")
            return {"error": str(e), "status": "failed", "paper_id": paper_id}

    @staticmethod
    def get_all_summaries() -> dict:
        """
        Retrieve all paper summaries from the database.

        Returns:
        - Dictionary with list of summaries and count
        """
        try:
            session = get_session()
            summaries = session.query(Summary).all()
            session.close()

            summaries_list = []
            for summary in summaries:
                summaries_list.append(
                    {
                        "id": summary.id,
                        "paper_id": summary.paper_id,
                        "summary_text": summary.summary_text,
                        "key_findings": summary.key_findings,
                        "methodology": summary.methodology,
                        "contributions": summary.contributions,
                        "limitations": summary.limitations,
                    }
                )

            logger.info(f"Retrieved {len(summaries_list)} summaries from database")

            return {
                "summaries": summaries_list,
                "count": len(summaries_list),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error retrieving all summaries: {str(e)}")
            return {"error": str(e), "status": "failed", "summaries": [], "count": 0}

    @staticmethod
    def store_synthesis(
        synthesis_text: str,
        common_themes: List[str],
        research_gaps: List[str],
        future_directions: List[str],
        papers_included: List[int],
        mini_survey: str = None,
    ) -> dict:
        """
        Store a cross-paper synthesis in the database.

        Parameters:
        - synthesis_text: Complete synthesis text
        - common_themes: List of identified themes
        - research_gaps: List of research gaps
        - future_directions: List of future opportunities
        - papers_included: List of paper IDs included in synthesis
        - mini_survey: Formatted mini-survey with citations (optional)

        Returns:
        - Dictionary with 'synthesis_id', 'status', 'error' (if any)
        """
        try:
            session = get_session()

            synthesis = Synthesis(
                synthesis_text=synthesis_text,
                common_themes=common_themes,
                research_gaps=research_gaps,
                future_directions=future_directions,
                mini_survey=mini_survey,
                papers_included=papers_included,
                paper_count=len(papers_included),
            )

            session.add(synthesis)
            session.commit()
            session.refresh(synthesis)

            synthesis_id = synthesis.id
            session.close()

            logger.info(
                f"Stored synthesis for {len(papers_included)} papers (Synthesis ID: {synthesis_id})"
            )

            return {
                "synthesis_id": synthesis_id,
                "papers_count": len(papers_included),
                "status": "success",
                "message": f"Synthesis stored successfully with ID {synthesis_id}",
            }

        except Exception as e:
            logger.error(f"Error storing synthesis: {str(e)}")
            return {"error": str(e), "status": "failed"}

    @staticmethod
    def get_latest_synthesis() -> dict:
        """
        Retrieve the most recent synthesis from the database.

        Returns:
        - Dictionary with synthesis data or error
        """
        try:
            session = get_session()
            synthesis = (
                session.query(Synthesis).order_by(Synthesis.created_at.desc()).first()
            )
            session.close()

            if not synthesis:
                logger.warning("No synthesis found in database")
                return {"error": "No synthesis found", "status": "not_found"}

            logger.info(f"Retrieved latest synthesis (ID: {synthesis.id})")

            return {
                "id": synthesis.id,
                "synthesis_text": synthesis.synthesis_text,
                "common_themes": synthesis.common_themes,
                "research_gaps": synthesis.research_gaps,
                "future_directions": synthesis.future_directions,
                "mini_survey": synthesis.mini_survey,
                "papers_included": synthesis.papers_included,
                "paper_count": synthesis.paper_count,
                "created_at": str(synthesis.created_at),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error retrieving latest synthesis: {str(e)}")
            return {"error": str(e), "status": "failed"}
