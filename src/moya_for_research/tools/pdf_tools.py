"""
PDF Tools for MOYA for Research paper analysis.

Hybrid approach:
- PyMuPDF (fitz) for content extraction (faster, better layout handling)
- PyPDF2 for metadata extraction (simple access to PDF metadata dictionary)
"""

import fitz  # PyMuPDF
import PyPDF2
from pathlib import Path
import re
from loguru import logger


class PDFTools:
    """Tools for PDF parsing and metadata extraction."""

    @staticmethod
    def parse_pdf(file_path: str) -> dict:
        """
        Parse a PDF file and extract structured content including text from all pages.

        Uses PyMuPDF (fitz) for accurate text extraction with better layout handling.

        Parameters:
        - file_path: Absolute path to the PDF file

        Returns:
        - Dictionary with 'text', 'page_count', 'file_name', 'status', 'error' (if any)
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"File not found: {file_path}")
                return {"error": f"File not found: {file_path}", "status": "failed"}

            logger.info(f"Parsing PDF: {path.name}")

            # Open PDF with PyMuPDF
            doc = fitz.open(str(path))
            page_count = len(doc)

            # Extract text from all pages
            full_text = ""
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                full_text += f"--- Page {page_num + 1} ---\n{page_text}\n\n"

            doc.close()

            logger.info(
                f"Successfully parsed PDF: {path.name} ({page_count} pages, {len(full_text)} chars)"
            )

            return {
                "text": full_text.strip(),
                "page_count": page_count,
                "file_name": path.name,
                "file_path": str(path),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {str(e)}")
            return {"error": str(e), "status": "failed", "file_path": file_path}

    @staticmethod
    def extract_metadata(file_path: str, pdf_text: str = None) -> dict:
        """
        Extract metadata (title, authors, abstract, year) from PDF.

        Uses PyPDF2 to access PDF metadata dictionary fields, with fallback to heuristics
        if metadata fields are empty or missing.

        Parameters:
        - file_path: Absolute path to the PDF file
        - pdf_text: Optional full text (if already extracted, to avoid re-parsing)

        Returns:
        - Dictionary with 'title', 'authors', 'abstract', 'year', 'status', 'error' (if any)
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"File not found: {file_path}")
                return {"error": f"File not found: {file_path}", "status": "failed"}

            logger.info(f"Extracting metadata from: {path.name}")

            # Try to extract from PDF metadata dictionary using PyPDF2
            pdf_metadata = {}
            try:
                with open(path, "rb") as file:
                    pdf_reader = PyPDF2.PdfReader(file)

                    if pdf_reader.metadata:
                        # Extract standard metadata fields
                        pdf_metadata = {
                            "title": pdf_reader.metadata.get("/Title", ""),
                            "author": pdf_reader.metadata.get("/Author", ""),
                            "subject": pdf_reader.metadata.get("/Subject", ""),
                            "creator": pdf_reader.metadata.get("/Creator", ""),
                            "producer": pdf_reader.metadata.get("/Producer", ""),
                            "creation_date": pdf_reader.metadata.get(
                                "/CreationDate", ""
                            ),
                        }
                        logger.debug(f"PDF metadata extracted: {pdf_metadata}")

            except Exception as e:
                logger.warning(f"Could not extract PDF metadata using PyPDF2: {str(e)}")

            # Use metadata if available, otherwise fall back to heuristics
            title = (
                pdf_metadata.get("title", "").strip()
                if pdf_metadata.get("title")
                else None
            )
            authors = (
                pdf_metadata.get("author", "").strip()
                if pdf_metadata.get("author")
                else None
            )
            abstract = (
                pdf_metadata.get("subject", "").strip()
                if pdf_metadata.get("subject")
                else None
            )

            # If metadata is missing or empty, use heuristic extraction from text
            if not title or not abstract:
                logger.info("PDF metadata incomplete, applying heuristics to text")

                # Get text if not provided
                if pdf_text is None:
                    parse_result = PDFTools.parse_pdf(file_path)
                    if parse_result["status"] == "failed":
                        return parse_result
                    pdf_text = parse_result["text"]

                # Apply heuristics
                heuristic_data = PDFTools._extract_metadata_heuristic(pdf_text)

                # Use heuristic data if metadata was empty
                if not title:
                    title = heuristic_data.get("title", "Unknown Title")
                if not authors:
                    authors = heuristic_data.get("authors", "Unknown Authors")
                if not abstract:
                    abstract = heuristic_data.get("abstract", "No abstract found")

                # Extract year from heuristics
                year = heuristic_data.get("year")
            else:
                # Try to extract year from creation date if available
                year = None
                if pdf_metadata.get("creation_date"):
                    year_match = re.search(r"20\d{2}", pdf_metadata["creation_date"])
                    if year_match:
                        year = int(year_match.group())

            logger.info(f"Metadata extracted for: {title[:50]}...")

            return {
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "year": year,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {str(e)}")
            return {"error": str(e), "status": "failed", "file_path": file_path}

    @staticmethod
    def _extract_metadata_heuristic(pdf_text: str) -> dict:
        """
        Extract metadata using heuristics when PDF metadata dictionary is empty.

        Heuristics:
        - Title: First non-empty line of reasonable length (< 200 chars)
        - Abstract: Text between "Abstract" and "Introduction"/"1. Introduction"
        - Year: First occurrence of 20XX pattern
        - Authors: Lines after title before abstract (basic extraction)

        Parameters:
        - pdf_text: Full text content of the PDF

        Returns:
        - Dictionary with heuristic-extracted metadata
        """
        lines = [line.strip() for line in pdf_text.split("\n") if line.strip()]

        # Extract title: First non-empty line with reasonable length
        title = "Unknown Title"
        for line in lines[:10]:  # Check first 10 lines
            if 10 < len(line) < 200 and not line.isupper():  # Avoid all-caps headers
                title = line
                break

        # Extract abstract: Text between "Abstract" and "Introduction"
        abstract = ""
        in_abstract = False
        abstract_lines = []

        for line in lines:
            line_lower = line.lower()

            # Start collecting at "abstract"
            if "abstract" in line_lower and len(line) < 50:
                in_abstract = True
                continue

            # Stop at introduction or numbered section
            if in_abstract and any(
                marker in line_lower
                for marker in ["introduction", "1.", "keywords", "1 introduction"]
            ):
                break

            if in_abstract:
                abstract_lines.append(line)

        abstract = " ".join(abstract_lines).strip() or "No abstract found"

        # Extract year: First occurrence of 20XX
        year = None
        year_match = re.search(
            r"20\d{2}", pdf_text[:3000]
        )  # Search in first 3000 chars
        if year_match:
            year = int(year_match.group())

        # Authors: Basic extraction (between title and abstract)
        authors = "Unknown Authors"  # Would require more sophisticated NER for accuracy

        return {
            "title": title,
            "authors": authors,
            "abstract": abstract[:500]
            if len(abstract) > 500
            else abstract,  # Limit abstract length
            "year": year,
        }
