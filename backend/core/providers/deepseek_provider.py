"""
Chatty — DeepSeek provider.

Uses DeepSeek's OpenAI-compatible API endpoint.

Streaming, tool calling, message formatting and tool result handling
are delegated to OpenAICompatibleProvider.
"""

import logging

import httpx
import openai

from core.providers.openai_compat import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


# Fallback models when /models API fails
DEEPSEEK_MODELS = [
    "deepseek-v4-pro",
    "deepseek-v4-flash",
]


class DeepSeekProvider(OpenAICompatibleProvider):

    def __init__(
        self,
        access_token: str,
        model: str = "deepseek-v4-flash",
    ):
        super().__init__(
            api_key=access_token,
            base_url=DEEPSEEK_BASE_URL,
            model=model,
        )

        self.access_token = access_token
        self.last_error: str | None = None

    @property
    def provider_name(self) -> str:
        return "deepseek"

    async def _fetch_models(self) -> list[str]:
        """
        Fetch models from DeepSeek API.
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
        Return available DeepSeek models.

        Falls back to local list when API does not expose models.
        """
        try:
            return await self._fetch_models()

        except Exception as e:
            logger.warning(
                "DeepSeek model listing failed: %s",
                e,
            )

            return DEEPSEEK_MODELS

    async def validate(self) -> bool:
        """
        Validate DeepSeek API key.

        Uses /models endpoint:
        - no token consumption
        - independent from selected model
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
                "DeepSeek validation failed: %s",
                self.last_error,
            )

            return False

        except Exception as e:
            self.last_error = str(e)

            logger.warning(
                "DeepSeek validation failed: %s",
                e,
            )

            return False