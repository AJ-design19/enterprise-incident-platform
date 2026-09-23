"""
Shared base class for all agents: wraps the local Ollama chat model,
enforces JSON-structured output where needed, and gives every agent
consistent retry/error handling.
"""
from __future__ import annotations

import json
import re
from typing import Any

from langchain_ollama import ChatOllama
from tenacity import retry, stop_after_attempt, wait_exponential

from config import ollama_config
from logging_setup import logger


class AgentError(RuntimeError):
    """Raised when an agent cannot produce a usable result after retries."""


class BaseAgent:
    """Common LLM plumbing. Subclasses implement `run(...)`."""

    name: str = "base_agent"
    system_prompt: str = "You are a helpful enterprise IT operations assistant."

    def __init__(self, model: str | None = None, temperature: float | None = None):
        self.llm = ChatOllama(
            base_url=ollama_config.host,
            model=model or ollama_config.model,
            temperature=temperature if temperature is not None else ollama_config.temperature,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _invoke(self, user_prompt: str, system_prompt: str | None = None) -> str:
        messages = [
            ("system", system_prompt or self.system_prompt),
            ("human", user_prompt),
        ]
        try:
            response = self.llm.invoke(messages)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[{self.name}] LLM invocation failed: {exc}")
            raise
        return response.content

    def _invoke_json(self, user_prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        """Invoke the LLM and parse a JSON object out of the response,
        tolerating markdown code fences and minor formatting noise."""
        raw = self._invoke(user_prompt, system_prompt)
        cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()

        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        candidate = match.group(0) if match else cleaned

        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            logger.error(f"[{self.name}] Failed to parse JSON from LLM output: {raw[:300]}")
            raise AgentError(f"{self.name} produced non-JSON output") from exc

    def run(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - interface method
        raise NotImplementedError
