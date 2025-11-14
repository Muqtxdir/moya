"""
Chat Agent for MOYA for Research.

Responsibilities:
- Answer questions about analyzed papers
- Provide insights from stored summaries and synthesis
- Interactive Q&A based on database contents

Uses OllamaToolAgent with database access tools and RAG-like fallback.
When tools fail or don't work properly, agent can answer directly from
preloaded database context (Retrieval Augmented Generation approach).
"""

import json
from typing import Optional, Dict, Any
from moya.agents.agent import Agent, AgentConfig
from moya.tools.tool import Tool
from moya.tools.tool_registry import ToolRegistry
from moya_for_research.tools.db_tools import DBTools
from moya_for_research.agents.ollama_tool_agent import OllamaToolAgent
from moya_for_research.config import settings
from loguru import logger


def create_chat_agent(context_data: Optional[Dict[str, Any]] = None) -> Agent:
    """
    Create the Chat Agent with database access tools and optional context.

    The Chat Agent is responsible for:
    1. Answering questions about analyzed papers
    2. Retrieving information from database (via tools or context)
    3. Providing insights from summaries and synthesis
    4. Interactive conversational Q&A

    Args:
        context_data: Optional preloaded database contents for RAG-like fallback
                     Should contain 'papers', 'summaries', and 'synthesis' keys

    Returns:
        Chat Agent with database tools and/or context
    """
    logger.info(f"Creating Chat Agent with Ollama ({settings.OLLAMA_MODEL})")

    # Create tool registry
    chat_tools = ToolRegistry()

    # Register database access tools
    chat_tools.register_tool(
        Tool(
            name="get_all_papers",
            function=DBTools.get_all_papers,
            description="""Get all papers from database.

            Returns:
                Dictionary with papers list and count

            Use this to see what papers are available.""",
        )
    )

    chat_tools.register_tool(
        Tool(
            name="get_paper",
            function=DBTools.get_paper,
            description="""Get a specific paper by ID. Call with paper_id as an integer (e.g., paper_id: 1 or paper_id: 2). Returns dictionary with paper details.""",
        )
    )

    chat_tools.register_tool(
        Tool(
            name="get_all_summaries",
            function=DBTools.get_all_summaries,
            description="""Get all paper summaries from database.

            Returns:
                Dictionary with summaries list and count

            Use this to see summaries of all analyzed papers.""",
        )
    )

    chat_tools.register_tool(
        Tool(
            name="get_summary",
            function=DBTools.get_summary,
            description="""Get summary for a specific paper. Call with paper_id as an integer (e.g., paper_id: 1 or paper_id: 2). Returns dictionary with summary_text, key_findings, methodology, contributions, limitations.""",
        )
    )

    chat_tools.register_tool(
        Tool(
            name="get_latest_synthesis",
            function=DBTools.get_latest_synthesis,
            description="""Get the latest cross-paper synthesis.

            Returns:
                Dictionary with synthesis (common_themes, research_gaps, future_directions, mini_survey)

            Use this to get the overall synthesis across all papers.""",
        )
    )

    # Build system prompt with optional context data (RAG-like approach)
    system_prompt_parts = [
        "You are a research assistant that helps users understand and explore analyzed research papers.",
        "",
        "Your responsibilities:",
        "1. Answer questions about the papers",
        "2. Help users find specific information",
        "3. Compare and contrast different papers",
        "4. Explain research findings clearly",
        "5. Reference specific papers when answering",
        "",
        "Guidelines:",
        "- Be helpful and conversational",
        "- Cite paper titles when referencing",
        "- Provide accurate information",
        "- If information isn't available, say so",
    ]

    # Add preloaded context if provided (RAG fallback)
    if context_data:
        logger.info("Adding preloaded database context to chat agent (RAG mode)")
        system_prompt_parts.extend([
            "",
            "=== DATABASE CONTENTS (Direct Access) ===",
            "",
            "You have direct access to the following database contents:",
            ""
        ])

        # Add papers
        if "papers" in context_data and context_data["papers"]:
            papers_data = context_data["papers"]
            system_prompt_parts.append(f"PAPERS ({len(papers_data)}):")
            for i, paper in enumerate(papers_data[:10], 1):  # Limit to 10 for context
                system_prompt_parts.append(
                    f"{i}. [{paper.get('id')}] {paper.get('title', 'Untitled')} "
                    f"by {paper.get('authors', 'Unknown')} ({paper.get('year', 'N/A')})"
                )
                if paper.get('abstract'):
                    abstract = paper['abstract'][:200] + "..." if len(paper['abstract']) > 200 else paper['abstract']
                    system_prompt_parts.append(f"   Abstract: {abstract}")
            system_prompt_parts.append("")

        # Add summaries
        if "summaries" in context_data and context_data["summaries"]:
            summaries_data = context_data["summaries"]
            system_prompt_parts.append(f"SUMMARIES ({len(summaries_data)}):")
            for i, summary in enumerate(summaries_data, 1):
                system_prompt_parts.append(f"{i}. Paper {summary.get('paper_id')}:")
                if summary.get('summary_text'):
                    system_prompt_parts.append(f"   Summary: {summary['summary_text'][:300]}...")
                if summary.get('key_findings'):
                    system_prompt_parts.append(f"   Key Findings: {summary['key_findings'][:200]}...")
            system_prompt_parts.append("")

        # Add synthesis
        if "synthesis" in context_data and context_data["synthesis"]:
            synthesis_data = context_data["synthesis"]
            system_prompt_parts.append("SYNTHESIS:")
            if synthesis_data.get('synthesis_text'):
                system_prompt_parts.append(f"Overview: {synthesis_data['synthesis_text'][:400]}...")
            if synthesis_data.get('common_themes'):
                themes = synthesis_data.get('common_themes', [])
                if themes:
                    system_prompt_parts.append(f"Themes: {', '.join(themes[:5])}")
            system_prompt_parts.append("")

        system_prompt_parts.extend([
            "You can answer questions directly from this context.",
            "Tools are also available if needed, but use the context when possible.",
            ""
        ])
    else:
        # No context provided, rely on tools
        system_prompt_parts.extend([
            "",
            "Available tools:",
            "- get_all_papers(): List all papers",
            "- get_paper(paper_id): Get details of specific paper",
            "- get_all_summaries(): List all summaries",
            "- get_summary(paper_id): Get summary of specific paper",
            "- get_latest_synthesis(): Get cross-paper analysis",
            "",
            "Use tools to retrieve accurate information when needed.",
        ])

    system_prompt = "\n".join(system_prompt_parts)

    # Create agent configuration
    config = AgentConfig(
        agent_name="chat",
        agent_type="ollama",
        description="Interactive chat agent for research paper Q&A",
        system_prompt=system_prompt,
        llm_config={
            "base_url": settings.OLLAMA_BASE_URL,
            "model_name": settings.OLLAMA_MODEL,
            "temperature": 0.3,  # Slightly higher for more natural conversation
            "max_tokens": settings.LLM_MAX_TOKENS,
        },
        tool_registry=chat_tools,
    )

    # Create Ollama agent
    agent = OllamaToolAgent(agent_config=config)

    logger.info("Chat Agent created successfully")
    return agent
