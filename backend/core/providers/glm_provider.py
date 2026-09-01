"""
Chatty — Zhipu GLM provider.

Uses Zhipu AI's OpenAI-compatible API endpoint.

Streaming, tool calling, message formatting and tool result handling
are delegated to OpenAICompatibleProvider.
"""

import logging

import httpx
import openai

from core.providers.openai_compat import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"


# Fallback models when /models API fails
GLM_MODELS = [
    "glm-5.3",
]


class GLMProvider(OpenAICompatibleProvider):

    def __init__(
        self,
        access_token: str,
        model: str = "glm-5.3",
    ):
        super().__init__(
            api_key=access_token,
            base_url=GLM_BASE_URL,
            model=model,
        )

        self.access_token = access_token
        self.last_error: str | None = None

    @property
    def provider_name(self) -> str:
        return "glm"

    async def _fetch_models(self) -> list[str]:
        """
        Fetch models from Zhipu GLM API.
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
        Return available GLM models.

        Falls back to local list when API does not expose models.
        """
        try:
            return await self._fetch_models()

        except Exception as e:
            logger.warning(
                "GLM model listing failed: %s",
                e,
            )

            return GLM_MODELS

    async def validate(self) -> bool:
        """
        Validate Zhipu GLM API key.

        Uses /models endpoint when available:
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
                "GLM validation failed: %s",
                self.last_error,
            )

            return False

        except Exception as e:
            self.last_error = str(e)

            logger.warning(
                "GLM validation failed: %s",
                e,
            )

            return False
