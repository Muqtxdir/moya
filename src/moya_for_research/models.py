"""
SQLAlchemy models for MOYA for Research paper storage.

Models:
- Paper: Stores research papers with full text and metadata
- Summary: Stores structured summaries of papers
- Synthesis: Stores cross-paper analysis and insights
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from moya_for_research.database import Base


class Paper(Base):
    """Research paper model."""

    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    authors = Column(String(1000))
    abstract = Column(Text)
    year = Column(Integer)
    full_text = Column(Text, nullable=False)
    file_path = Column(String(500))
    file_name = Column(String(255))
    page_count = Column(Integer)
    extra_metadata = Column(
        JSON
    )  # Additional metadata as JSON (renamed from 'metadata' to avoid SQLAlchemy conflict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    summaries = relationship(
        "Summary", back_populates="paper", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Paper(id={self.id}, title='{self.title[:50]}...')>"


class Summary(Base):
    """Paper summary model."""

    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, index=True)

    # Summary content
    summary_text = Column(Text, nullable=False)
    key_findings = Column(Text)
    methodology = Column(Text)
    contributions = Column(Text)
    limitations = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    paper = relationship("Paper", back_populates="summaries")

    def __repr__(self):
        return f"<Summary(id={self.id}, paper_id={self.paper_id})>"


class Synthesis(Base):
    """Cross-paper synthesis model."""

    __tablename__ = "synthesis"

    id = Column(Integer, primary_key=True, index=True)

    # Synthesis content
    synthesis_text = Column(Text, nullable=False)
    common_themes = Column(JSON)  # List of themes
    research_gaps = Column(JSON)  # List of identified gaps
    future_directions = Column(JSON)  # List of opportunities
    mini_survey = Column(Text, nullable=True)  # Formatted mini-survey with citations

    # Metadata
    papers_included = Column(JSON)  # List of paper IDs
    paper_count = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Synthesis(id={self.id}, papers={self.paper_count})>"
