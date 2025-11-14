"""
Ollama Agent with Tool Calling Support for MOYA for Research.

This extends MOYA's OllamaAgent to add tool calling capabilities
by using prompt engineering to guide the model to request tools in JSON format.
"""

import json
from typing import Any, Dict, List

import requests
from loguru import logger
from moya.agents.agent import Agent, AgentConfig
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class OllamaToolAgent(Agent):
    """
    Ollama agent with tool calling support via prompt engineering.

    The agent is instructed to output tool calls in JSON format:
    {"tool_call": {"name": "tool_name", "arguments": {...}}}

    When the agent needs to use a tool, it outputs this JSON.
    We parse it, execute the tool, and feed the result back.
    """

    def __init__(self, agent_config: AgentConfig):
        """Initialize Ollama agent with tool calling support."""
        super().__init__(agent_config)

        # Get Ollama configuration from llm_config
        self.base_url = self.llm_config.get("base_url", "http://localhost:11434")
        self.model_name = self.llm_config.get("model_name", "qwen2.5:3b")
        self.max_iterations = 5

        # Test Ollama connection
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise ConnectionError("Unable to connect to Ollama server")
            logger.info(f"Connected to Ollama at {self.base_url}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Ollama server: {str(e)}")

    def get_tool_definitions_text(self) -> str:
        """
        Format tools as text for the prompt.

        Returns:
            str: Tool definitions in a format the LLM can understand
        """
        if not self.tool_registry:
            return "No tools available."

        tools = self.tool_registry.get_tools()
        if not tools:
            return "No tools available."

        tool_descriptions = []
        for tool in tools:
            # Only include description, not detailed parameter schemas
            # Small models get confused by schemas and copy them as values
            tool_descriptions.append(f"- {tool.name}: {tool.description}")

        return "\n".join(tool_descriptions)

    def create_system_prompt_with_tools(self) -> str:
        """
        Create enhanced system prompt that includes tool calling instructions.

        Returns:
            str: Complete system prompt with tool usage guidelines
        """
        tools_text = self.get_tool_definitions_text()

        prompt = f"""{self.system_prompt}

## Available Tools

You have access to the following tools:

{tools_text}

## Tool Calling Instructions

When you need to use a tool, output ONLY a JSON object in this EXACT format:
{{"tool_call": {{"name": "tool_name", "arguments": {{"param_name": "value"}}}}}}

CRITICAL RULES:
1. Output ONLY JSON - no text before or after
2. Use EXACT tool names from the list above
3. Use EXACT parameter names shown in the examples (e.g., "file_path" NOT "path" or "paper_path")
4. Copy parameter names EXACTLY from the tool descriptions
5. After tool execution, you'll receive the result and can continue

If you don't need a tool, respond normally with text."""

        return prompt

    def handle_message(self, message: str, **kwargs) -> str:
        """
        Handle message with tool calling support.

        Args:
            message: User message

        Returns:
            str: Final response after tool execution loop
        """
        # If no tools registered, skip tool calling entirely
        if not self.tool_registry:
            logger.debug("No tools registered, using direct generation mode")
            conversation = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": message},
            ]
            return self._call_ollama(conversation)

        # Build conversation with enhanced system prompt
        conversation = [
            {"role": "system", "content": self.create_system_prompt_with_tools()},
            {"role": "user", "content": message},
        ]

        iteration = 0

        while iteration < self.max_iterations:
            logger.debug(
                f"Tool calling iteration {iteration + 1}/{self.max_iterations}"
            )

            # Get response from Ollama
            response_text = self._call_ollama(conversation)

            # Add assistant response to conversation
            conversation.append({"role": "assistant", "content": response_text})

            # Check if response contains a tool call
            tool_call = self._parse_tool_call(response_text)

            if tool_call:
                # Execute the tool
                tool_result = self._execute_tool(tool_call)

                # Add tool result to conversation
                conversation.append(
                    {
                        "role": "user",
                        "content": f"Tool '{tool_call['name']}' returned: {tool_result}",
                    }
                )

                iteration += 1
            else:
                # No tool call, return the response
                return response_text

        # Max iterations reached
        logger.warning(f"Reached max iterations ({self.max_iterations})")
        return conversation[-1]["content"]

    @retry(
        retry=retry_if_exception_type(
            (requests.exceptions.RequestException, requests.exceptions.Timeout)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _call_ollama(self, conversation: List[Dict]) -> str:
        """
        Call Ollama API with conversation history.

        Retries up to 3 times with exponential backoff on connection errors.

        Args:
            conversation: List of message dicts with role and content

        Returns:
            str: Response from Ollama
        """
        # Combine conversation into a single prompt
        # Ollama's /api/generate doesn't support chat format well,
        # so we concatenate messages
        prompt_parts = []
        for msg in conversation:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        prompt_parts.append("Assistant:")
        full_prompt = "\n\n".join(prompt_parts)

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.llm_config.get("temperature", 0.0),
                        "num_predict": self.llm_config.get("max_tokens", 4000),
                    },
                },
                timeout=600,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API error: {str(e)}")
            raise  # Let tenacity handle the retry
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return f"[Error calling Ollama: {str(e)}]"

    def _parse_tool_call(self, response: str) -> Dict[str, Any] | None:
        """
        Parse tool call from response if present.

        Args:
            response: Response text from LLM

        Returns:
            dict: Tool call dict with 'name' and 'arguments', or None
        """
        # Look for JSON tool call pattern
        # {"tool_call": {"name": "...", "arguments": {...}}}

        # Try multiple extraction methods

        # Method 1: Try to extract complete JSON object
        try:
            # Find all potential JSON objects
            brace_count = 0
            start_idx = None

            for i, char in enumerate(response):
                if char == "{":
                    if brace_count == 0:
                        start_idx = i
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0 and start_idx is not None:
                        # Found complete JSON object
                        json_str = response[start_idx : i + 1]
                        try:
                            parsed = json.loads(json_str)
                            if "tool_call" in parsed:
                                tool_call = parsed["tool_call"]
                                if "name" in tool_call and "arguments" in tool_call:
                                    logger.info(f"Tool call: {tool_call['name']}")
                                    return tool_call
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.debug(f"Method 1 failed: {e}")

        # Method 2: Try parsing entire response as JSON
        try:
            response_clean = response.strip()
            if response_clean.startswith("{") and response_clean.endswith("}"):
                parsed = json.loads(response_clean)
                if "tool_call" in parsed:
                    tool_call = parsed["tool_call"]
                    if "name" in tool_call and "arguments" in tool_call:
                        logger.info(f"Tool call: {tool_call['name']}")
                        return tool_call
        except json.JSONDecodeError:
            pass

        return None

    def _execute_tool(self, tool_call: Dict[str, Any]) -> str:
        """
        Execute a tool and return its result.

        Args:
            tool_call: Dict with 'name' and 'arguments'

        Returns:
            str: Tool execution result
        """
        tool_name = tool_call["name"]
        arguments = tool_call.get("arguments", {})

        try:
            # Safety check - should not happen if handle_message works correctly
            if not self.tool_registry:
                return "Error: No tools available (agent in content generation mode)"

            tool = self.tool_registry.get_tool(tool_name)

            if not tool:
                return f"Error: Tool '{tool_name}' not found"

            # Check if model passed schema instead of actual values
            # Small models sometimes copy parameter descriptions as values
            for key, value in arguments.items():
                if isinstance(value, dict) and "type" in value and "description" in value:
                    logger.warning(f"Model passed schema instead of value for {key}")
                    return f"Error: Please provide an actual value for '{key}', not the parameter schema. For example, if asking about paper 2, use paper_id: 2"

            # Fix common parameter name mistakes from small models
            # Tool-specific corrections
            if tool_name in ["parse_pdf", "extract_metadata"]:
                # These tools need file_path parameter
                param_corrections = {
                    "paper_path": "file_path",
                    "path": "file_path",
                    "pdf_path": "file_path",
                }
                corrected_args = {}
                for key, value in arguments.items():
                    corrected_key = param_corrections.get(key, key)
                    corrected_args[corrected_key] = value
                    if corrected_key != key:
                        logger.debug(f"Corrected parameter: {key} -> {corrected_key}")
            elif tool_name == "prepare_papers_for_analysis":
                # This tool needs papers_data parameter
                corrected_args = {}
                for key, value in arguments.items():
                    corrected_key = "papers_data" if key == "papers" else key
                    corrected_args[corrected_key] = value
            elif tool_name == "prepare_summaries_for_synthesis":
                # This tool needs summaries_data parameter
                corrected_args = {}
                for key, value in arguments.items():
                    corrected_key = "summaries_data" if key == "summaries" else key
                    corrected_args[corrected_key] = value
            elif tool_name in ["get_all_papers", "get_all_summaries"]:
                # These tools take NO parameters - ignore any arguments
                corrected_args = {}
                if arguments:
                    logger.debug(
                        f"Ignoring arguments for {tool_name} (takes no params)"
                    )
            else:
                # No corrections needed
                corrected_args = arguments

            # Execute the tool
            logger.info(f"Executing tool: {tool_name} with args: {corrected_args}")
            result = tool.function(**corrected_args)

            # Convert result to string if needed
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2)
            return str(result)

        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            return f"Error executing tool '{tool_name}': {str(e)}"

    def handle_message_stream(self, message: str, **kwargs):
        """Streaming not implemented for tool-calling Ollama agent."""
        # For simplicity, just call non-streaming version
        result = self.handle_message(message, **kwargs)
        yield result
