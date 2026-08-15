"""
Chatty — Ollama provider for local models.

Connects to a local Ollama instance via its OpenAI-compatible API.
Users run models on their own hardware for free.
"""

import logging
from typing import AsyncGenerator

import httpx

from core.providers.openai_compat import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

TOOL_CAPABLE_FAMILIES = [
    "llama3.1", "llama3.2", "llama3.3", "llama4",
    "qwen2.5", "qwen3", "qwen3.5",
    "mistral", "mistral-nemo", "mistral-small", "mistral-large",
    "command-r", "command-r-plus",
    "phi4",
    "nemotron",
    "hermes3",
    "firefunction",
]


def _is_tool_capable(model_name: str) -> bool:
    """Check if a model name matches a known tool-capable family."""
    base = model_name.split(":")[0].lower()
    return any(base == family or base.startswith(family + "-") for family in TOOL_CAPABLE_FAMILIES)


class OllamaProvider(OpenAICompatibleProvider):
    _tool_support_cache: dict[str, bool] = {}

    def __init__(self, base_url: str = "http://localhost:11434", model: str = ""):

        self.ollama_url = base_url.rstrip("/")

        super().__init__(
            api_key="ollama",
            base_url=f"{self.ollama_url}/v1",
            model=model,
        )

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def _recommend_tool_models(self) -> str:
        """Build a recommendation string for tool-capable models."""
        try:
            installed = await self.list_models()
        except Exception:
            installed = []
        capable = [m for m in installed if _is_tool_capable(m)]
        if capable:
            model_list = ", ".join(f"**{m}**" for m in capable[:5])
            return (
                f"{self.model} doesn't support tool calling, which Chatty needs for "
                f"memory, search, and integrations. "
                f"Switch to a tool-capable model: {model_list}"
            )
        return (
            f"{self.model} doesn't support tool calling, which Chatty needs for "
            f"memory, search, and integrations. "
            f"Install a compatible model: `ollama pull llama3.1` or `ollama pull qwen3.5`"
        )

    async def stream_turn(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: str | tuple[str, str],
    ) -> AsyncGenerator[dict, None]:

        if not self.model:
            models = await self.list_models()

            chat_models = [
                m for m in models
                if not any(
                    x in m.lower()
                    for x in [
                        "embed",
                        "embedding",
                        "nomic",
                        "bge",
                        "gte",
                    ]
                )
            ]

            if chat_models:
                self.model = chat_models[0]
            elif models:
                self.model = models[0]
            logger.info("Auto selected Ollama model: %s", self.model)

        # Skip tools for models known not to support them
        model_known_no_tools = OllamaProvider._tool_support_cache.get(self.model) is False
        effective_tools = [] if model_known_no_tools else tools


        async for event in super().stream_turn(
            messages=messages,
            tools=effective_tools,
            system_prompt=system_prompt,
        ):
            # Detect "does not support tools" and retry without them
            if (
                event.get("type") == "error"
                and "does not support tools" in event.get("error", "")
                and effective_tools
            ):
                OllamaProvider._tool_support_cache[self.model] = False
                yield {"type": "error", "error": await self._recommend_tool_models()}
                return

            if event.get("type") == "error" and event.get("error") == "connection_error":
                yield {
                    "type": "error",
                    "error": f"Cannot connect to Ollama at {self.ollama_url}. Is it running? Start with: ollama serve",
                }
            else:
                yield event

    async def list_models(self) -> list[str]:
        """Return locally-installed Ollama model names."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.ollama_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.warning("Failed to list Ollama models: %s", e)
            return []

    async def validate(self) -> bool:
        """Check if Ollama is reachable (no inference burn)."""
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{self.ollama_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
