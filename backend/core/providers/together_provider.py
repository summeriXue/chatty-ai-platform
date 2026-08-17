"""
Chatty - Together AI provider for hosted open-weight models.

Uses Together AI's OpenAI-compatible API to run open-weight models
in the cloud at a fraction of the cost of proprietary APIs.

Streaming, tool calling, message formatting and tool result handling
are delegated to OpenAICompatibleProvider.

Together-specific model discovery and error handling remain here.
"""

import logging
from typing import AsyncGenerator

import httpx

from core.providers.openai_compat import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


TOGETHER_BASE_URL = "https://api.together.xyz/v1"


# Curated list of models known to work well with tool calling and agents.
#
# Every entry MUST be documented by Together as supporting function calling.
# Chatty always sends tools, so chat models without tool-calling support
# cannot be used reliably by agents.
TOGETHER_MODELS = [
    "moonshotai/Kimi-K2.6",
    "zai-org/GLM-5.2",
    "deepseek-ai/DeepSeek-V4-Pro",
    "MiniMaxAI/MiniMax-M3",
    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "google/gemma-4-31B-it",
    "openai/gpt-oss-120b",
    "Qwen/Qwen3.5-9B",
]

TOGETHER_DEFAULT_MODEL = "Qwen/Qwen3.5-9B"


# Together's catalog is large and mixes chat, embedding, image, rerank, etc.
# Prefer the per-model `type` when present; otherwise exclude obvious
# non-chat model ids by name.
_TOGETHER_NON_CHAT = (
    "embedding",
    "rerank",
    "image",
    "audio",
    "moderation",
    "whisper",
    "guard",
    "vision",
    "tts",
    "flux",
)


def _is_no_tool_support(error: str) -> bool:
    """
    Detect Together's error for a model served without tool calling enabled.
    """
    low = error.lower()

    return (
        "enable-auto-tool-choice" in low
        or "tool-call-parser" in low
    )


def _is_together_chat(model: dict) -> bool:
    """
    Return True when a Together catalog entry looks like a chat/language model.
    """
    mtype = model.get("type")

    if mtype:
        return mtype in ("chat", "language")

    low = model.get("id", "").lower()

    return not any(
        token in low
        for token in _TOGETHER_NON_CHAT
    )


class TogetherProvider(OpenAICompatibleProvider):

    def __init__(
        self,
        api_key: str,
        model: str = TOGETHER_DEFAULT_MODEL,
    ):
        super().__init__(
            api_key=api_key,
            base_url=TOGETHER_BASE_URL,
            model=model,
        )

        # Set by validate() on failure so router.py can surface
        # the real cause instead of a generic invalid-key message.
        self.last_error: str | None = None

    @property
    def provider_name(self) -> str:
        return "together"

    async def stream_turn(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: str | tuple[str, str],
    ) -> AsyncGenerator[dict, None]:
        """
        Reuse the OpenAI-compatible streaming implementation while translating
        Together-specific errors into clearer user-facing messages.
        """

        async for event in super().stream_turn(
            messages=messages,
            tools=tools,
            system_prompt=system_prompt,
            max_tokens=8192,
        ):
            if (
                event.get("type") == "error"
                and event.get("error") == "connection_error"
            ):
                yield {
                    "type": "error",
                    "error": (
                        "Cannot connect to Together AI. "
                        "Check your internet connection."
                    ),
                }

            elif (
                event.get("type") == "error"
                and _is_no_tool_support(event.get("error", ""))
            ):
                yield {
                    "type": "error",
                    "error": (
                        f"{self.model} does not support tool calling, "
                        f"which Chatty needs for memory, search, and integrations. "
                        f"Pick a model Together lists with function calling - "
                        f"e.g. {', '.join(TOGETHER_MODELS[:3])}."
                    ),
                }

            else:
                yield event

    async def _list_models_raw(self) -> list[dict]:
        """
        Fetch Together's raw model catalog.

        Together's /v1/models response is not fully OpenAI-compatible:
        it may return a bare JSON array instead of the OpenAI-style
        {"object": "list", "data": [...]} response.

        Therefore model listing uses httpx directly even though chat
        completions use the shared OpenAI-compatible implementation.
        """

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{TOGETHER_BASE_URL}/models",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                },
            )

        resp.raise_for_status()

        data = resp.json()

        if isinstance(data, list):
            return data

        return data.get("data", [])

    async def _fetch_models(self) -> list[str]:
        """
        Fetch and filter Together chat/language models.
        """

        models = await self._list_models_raw()

        return sorted(
            model["id"]
            for model in models
            if _is_together_chat(model)
        )

    async def list_models(self) -> list[str]:
        """
        Return Together models with caching and inferred tier materialization.
        """

        from core.providers.model_listing import (
            cache_key,
            cached_models,
            materialize_inference,
        )

        key = cache_key(
            "together",
            self.api_key,
        )

        models, is_live = await cached_models(
            key,
            self._fetch_models,
            TOGETHER_MODELS,
        )

        materialize_inference(
            "together",
            models,
            is_live,
        )

        return models

    async def validate(self) -> bool:
        """
        Validate the Together API key with its model-list endpoint.

        Chat completions are OpenAI-compatible, but Together's model-list
        response has its own shape, so validation deliberately goes through
        _list_models_raw().
        """

        self.last_error = None

        try:
            await self._list_models_raw()

            return True

        except httpx.HTTPStatusError as e:
            self.last_error = (
                f"HTTP {e.response.status_code}: "
                f"{e.response.text[:200]}"
            )

            logger.warning(
                "Together AI key validation failed: %s",
                self.last_error,
            )

            return False

        except Exception as e:
            self.last_error = str(e)

            logger.warning(
                "Together AI key validation failed: %s",
                e,
            )

            return False
