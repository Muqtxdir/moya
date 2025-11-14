"""
Parser Agent for MOYA for Research.

Responsibilities:
- Parse PDF files and extract content
- Extract metadata (title, authors, abstract, year)
- Store parsed papers in database

Uses OllamaToolAgent with local Ollama models.
"""

from moya.agents.agent import Agent, AgentConfig
from moya.tools.tool import Tool
from moya.tools.tool_registry import ToolRegistry
from moya_for_research.tools.pdf_tools import PDFTools
from moya_for_research.tools.db_tools import DBTools
from moya_for_research.agents.ollama_tool_agent import (
    OllamaToolAgent,
)
from moya_for_research.config import settings
from loguru import logger


def create_parser_agent() -> Agent:
    """
    Create the Parser Agent with PDF and database tools.

    The Parser Agent is responsible for:
    1. Parsing PDF files using PyMuPDF (content) and PyPDF2 (metadata)
    2. Extracting structured metadata
    3. Storing papers in the database

    Returns:
        OllamaToolAgent configured with parsing tools
    """
    logger.info(f"Creating Parser Agent with Ollama ({settings.OLLAMA_MODEL})")

    # Create tool registry for parser agent
    parser_tools = ToolRegistry()

    # Register PDF parsing tools
    parser_tools.register_tool(
        Tool(
            name="parse_pdf",
            function=PDFTools.parse_pdf,
            description='Parse a PDF file and extract all text content. REQUIRED PARAMETER: "file_path" (string). Example: {"file_path": "/path/to/paper.pdf"}',
        )
    )

    parser_tools.register_tool(
        Tool(
            name="extract_metadata",
            function=PDFTools.extract_metadata,
            description='Extract metadata from a PDF file. REQUIRED PARAMETER: "file_path" (string). Example: {"file_path": "/path/to/paper.pdf"}',
        )
    )

    # Register database storage tool
    parser_tools.register_tool(
        Tool(
            name="store_paper",
            function=DBTools.store_paper,
            description='Store a paper in database. REQUIRED PARAMETERS: "title" (string), "authors" (string), "abstract" (string), "full_text" (string), "file_path" (string), "file_name" (string), "page_count" (integer), "year" (integer). Example: {"title": "Paper Title", "authors": "John Doe", "abstract": "...", "full_text": "...", "file_path": "/path/paper.pdf", "file_name": "paper.pdf", "page_count": 10, "year": 2024}',
        )
    )

    system_prompt = """You are the Parser Agent in a research paper analysis system.

Your responsibilities:
1. Parse PDF files to extract complete text content
2. Extract structured metadata (title, authors, abstract, publication year)
3. Store the parsed paper in the database

When given a file path, follow this workflow:
1. Call parse_pdf(file_path) to extract the full text
2. Call extract_metadata(file_path) to get title, authors, abstract, and year
3. Call store_paper() with all the extracted information

Always:
- Verify that parsing succeeded before extracting metadata
- Check that all required fields are present before storing
- Provide clear feedback about what was done
- Report any errors encountered

If metadata extraction fails or returns incomplete data, still store the paper with whatever information is available.

Be concise in your responses and focus on the task at hand."""

    config = AgentConfig(
        agent_name="parser",
        agent_type="ollama",
        description="Parses research papers from PDF files",
        system_prompt=system_prompt,
        llm_config={
            "base_url": settings.OLLAMA_BASE_URL,
            "model_name": settings.OLLAMA_MODEL,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
        },
        tool_registry=parser_tools,
    )

    agent = OllamaToolAgent(agent_config=config)

    logger.info(f"Parser Agent created with {len(parser_tools.get_tools())} tools")

    return agent
