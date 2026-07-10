"""AI infrastructure adapters for Ollama local LLM and mock simulation."""

from yukinoaaa.infrastructure.ai.mock_adapter import MockAIAdapter
from yukinoaaa.infrastructure.ai.ollama_adapter import OllamaAIAdapter

__all__ = ["MockAIAdapter", "OllamaAIAdapter"]
