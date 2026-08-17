"""
Chatty - Kimi provider.

Uses Kimi's OpenAI-compatible API endpoint.

Streaming, tool calling, message formatting and tool result handling
are delegated to OpenAICompatibleProvider.
"""

import logging

import httpx
import openai

from core.providers.openai_compat import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


KIMI_BASE_URL = "https://api.moonshot.ai/v1"


# Fallback models when /models API fails.
# Keep this list small; live /models results take precedence.
KIMI_MODELS = [
    "kimi-k3",
]


class KimiProvider(OpenAICompatibleProvider):

    def __init__(
        self,
        access_token: str,
        model: str = "kimi-k3",
    ):
        super().__init__(
            api_key=access_token,
            base_url=KIMI_BASE_URL,
            model=model,
        )

        self.access_token = access_token
        self.last_error: str | None = None

    @property
    def provider_name(self) -> str:
        return "kimi"

    async def _fetch_models(self) -> list[str]:
        """
        Fetch models from Kimi API.
        """
        client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        response = await client.models.list()

        return [
            model.id
            for model in response.data
        ]

    async def list_models(self) -> list[str]:
        """
        Return available Kimi models.

        Falls back to a local list when model listing fails.
        """
        try:
            return await self._fetch_models()

        except Exception as e:
            logger.warning(
                "Kimi model listing failed: %s",
                e,
            )

            return KIMI_MODELS

    async def validate(self) -> bool:
        """
        Validate Kimi API key using the /models endpoint.
        """
        self.last_error = None

        try:
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )

            client.models.list()

            return True

        except httpx.HTTPStatusError as e:
            self.last_error = (
                f"HTTP {e.response.status_code}: "
                f"{e.response.text[:200]}"
            )

            logger.warning(
                "Kimi validation failed: %s",
                self.last_error,
            )

            return False

        except Exception as e:
            self.last_error = str(e)

            logger.warning(
                "Kimi validation failed: %s",
                e,
            )

            return False
        