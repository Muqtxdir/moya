"""
Summarizer Agent for MOYA for Research.

Responsibilities:
- Analyze paper content provided in the prompt
- Generate structured summaries with key findings, methodology, contributions, limitations
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


def create_summarizer_agent() -> Agent:
    """
    Create the Summarizer Agent for content generation.

    The Summarizer Agent is responsible for:
    1. Analyzing paper content provided in the message
    2. Generating structured summaries
    3. Returning formatted text (orchestrator handles storage)

    Returns:
        OllamaToolAgent configured for content generation (no tools)
    """
    logger.info(f"Creating Summarizer Agent with Ollama ({settings.OLLAMA_MODEL})")

    system_prompt = """You are a research paper summarizer. Analyze papers and provide structured summaries.

Output format:
SUMMARY: [2-3 sentence overview of the paper's main contribution and findings]
KEY_FINDINGS: [Bullet points of main results and discoveries]
METHODOLOGY: [Research methods and approaches used]
CONTRIBUTIONS: [Novel contributions to the field]
LIMITATIONS: [Limitations and future work needed]

Guidelines:
- Be concise and technical
- Focus on facts, not opinions
- Do not ask questions or suggest follow-ups
- Output only the structured analysis
- Do not attempt to call any tools
- Generate the summary directly based on the paper content provided"""

    config = AgentConfig(
        agent_name="summarizer",
        agent_type="ollama",
        description="Generates structured summaries of research papers",
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

    logger.info("Summarizer Agent created (content generation mode, no tools)")

    return agent
