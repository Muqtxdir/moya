"""
Synthesis Agent for MOYA for Research.

Responsibilities:
- Analyze papers and summaries provided in the prompt
- Identify common themes and patterns
- Find research gaps
- Propose future directions
- Generate mini-survey with citations
- Return structured text for orchestrator to store

Uses OllamaToolAgent with local Ollama models.
NO TOOLS - Pure content generation to avoid confusion with small models.
"""

from moya.agents.agent import Agent, AgentConfig
from moya_for_research.agents.ollama_tool_agent import (
    OllamaToolAgent,
)
from moya_for_research.config import settings
from loguru import logger


def create_synthesis_agent() -> Agent:
    """
    Create the Synthesis Agent for content generation.

    The Synthesis Agent is responsible for:
    1. Analyzing papers and summaries provided in the message
    2. Identifying cross-paper patterns and themes
    3. Finding research gaps
    4. Proposing future research directions
    5. Generating formatted mini-survey
    6. Returning formatted text (orchestrator handles storage)

    Returns:
        OllamaToolAgent configured for content generation (no tools)
    """
    logger.info(f"Creating Synthesis Agent with Ollama ({settings.OLLAMA_MODEL})")

    system_prompt = """You are a research synthesis analyzer. Analyze multiple papers to identify themes, gaps, and future directions.

Output format:
SYNTHESIS: [500-800 word analysis comparing papers, identifying patterns, discussing common approaches and divergent findings. Reference specific paper titles.]
THEMES: [List 3-5 common themes, one per line with dash. Be specific.]
GAPS: [List 3-5 research gaps, one per line with dash. Be concrete.]
DIRECTIONS: [List 3-5 future directions, one per line with dash. Be actionable.]

Guidelines:
- Reference papers by title in the synthesis
- Identify patterns and divergences
- Be specific and technical
- Do not ask questions or suggest follow-ups
- Output only the structured analysis
- Do not attempt to call any tools
- Generate the synthesis directly based on the papers and summaries provided"""

    config = AgentConfig(
        agent_name="synthesis",
        agent_type="ollama",
        description="Synthesizes insights across multiple research papers",
        system_prompt=system_prompt,
        llm_config={
            "base_url": settings.OLLAMA_BASE_URL,
            "model_name": settings.OLLAMA_MODEL,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
        },
        tool_registry=None,  # No tools - pure content generation
    )

    agent = OllamaToolAgent(agent_config=config)

    logger.info("Synthesis Agent created (content generation mode, no tools)")

    return agent
