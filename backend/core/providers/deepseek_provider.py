"""
Chatty — DeepSeek provider.

Uses OpenAI-compatible API endpoint.
Supports streaming and function calling.
"""

import json
import logging
from typing import AsyncGenerator

import openai

from core.providers.base import AIProvider

logger = logging.getLogger(__name__)


DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

DEEPSEEK_MODELS = [
    "deepseek-v4-pro",
    "deepseek-v4-flash",
]


def _ensure_array_items(schema: dict) -> dict:
    """Recursively ensure all array types have an items field."""
    if not isinstance(schema, dict):
        return schema

    result = dict(schema)

    if result.get("type") == "array" and "items" not in result:
        result["items"] = {}

    if "properties" in result:
        result["properties"] = {
            k: _ensure_array_items(v)
            for k, v in result["properties"].items()
        }

    if "items" in result and isinstance(result["items"], dict):
        result["items"] = _ensure_array_items(result["items"])

    return result


class DeepSeekProvider(AIProvider):

    def __init__(
        self,
        access_token: str,
        model: str = "deepseek-v4-flash",
    ):
        super().__init__(model=model)
        self.access_token = access_token


    def _build_client_kwargs(self) -> dict:
        return {
            "api_key": self.access_token,
            "base_url": DEEPSEEK_BASE_URL,
        }


    @property
    def provider_name(self) -> str:
        return "deepseek"


    def _format_tools(self, tools: list[dict]) -> list[dict]:
        """
        Convert Chatty internal tools format
        into OpenAI compatible function calling format.
        """

        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": _ensure_array_items(
                        t.get(
                            "input_schema",
                            {
                                "type": "object",
                                "properties": {}
                            }
                        )
                    ),
                },
            }
            for t in tools
        ]


    async def stream_turn(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: "str | tuple[str, str]",
    ) -> AsyncGenerator[dict, None]:

        client = openai.AsyncOpenAI(
            **self._build_client_kwargs()
        )

        deepseek_tools = self._format_tools(tools)


        if isinstance(system_prompt, tuple):
            system_prompt = "\n".join(system_prompt)


        api_messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]


        for m in messages:

            role = m.get("role")

            if role == "user":
                api_messages.append({
                    "role": "user",
                    "content": m.get("content", "")
                })

            elif role == "assistant":

                msg = {
                    "role": "assistant"
                }

                if m.get("content") is not None:
                    msg["content"] = m["content"]

                if m.get("tool_calls"):
                    msg["tool_calls"] = m["tool_calls"]

                api_messages.append(msg)


            elif role == "tool":

                api_messages.append({
                    "role": "tool",
                    "tool_call_id": m.get("tool_call_id", ""),
                    "content": m.get("content", "")
                })


        tool_calls = []


        try:

            kwargs = {
                "model": self.model,
                "messages": api_messages,
                "stream": True,
                "max_tokens": 16384,
            }


            if deepseek_tools:
                kwargs["tools"] = deepseek_tools


            stream = await client.chat.completions.create(
                **kwargs
            )


            async for chunk in stream:

                delta = (
                    chunk.choices[0].delta
                    if chunk.choices
                    else None
                )

                if not delta:
                    continue


                if delta.content:
                    yield {
                        "type": "text",
                        "text": delta.content
                    }


                if delta.tool_calls:

                    for tc_delta in delta.tool_calls:

                        idx = tc_delta.index


                        while len(tool_calls) <= idx:
                            tool_calls.append(
                                {
                                    "id": "",
                                    "name": "",
                                    "input_json": ""
                                }
                            )


                        if tc_delta.id:
                            tool_calls[idx]["id"] = tc_delta.id


                        if tc_delta.function:

                            if tc_delta.function.name:

                                tool_calls[idx]["name"] = (
                                    tc_delta.function.name
                                )

                                yield {
                                    "type": "tool_start",
                                    "tool": tc_delta.function.name,
                                    "tool_use_id": tc_delta.id or ""
                                }


                            if tc_delta.function.arguments:

                                tool_calls[idx]["input_json"] += (
                                    tc_delta.function.arguments
                                )



            for tc in tool_calls:

                if tc.get("input_json"):

                    try:

                        tc["args"] = json.loads(
                            tc["input_json"]
                        )

                        yield {
                            "type": "tool_args",
                            "tool": tc["name"],
                            "tool_use_id": tc["id"],
                            "args": tc["args"],
                        }

                    except Exception:

                        tc["args"] = {}



            yield {
                "type": "_turn_complete",
                "tool_calls": tool_calls,
                "stop_reason":
                    "tool_use" if tool_calls else "stop",
            }



        except openai.RateLimitError:

            yield {
                "type": "error",
                "error":
                    "DeepSeek rate limit reached."
            }

            yield {
                "type": "_turn_complete",
                "tool_calls": [],
                "stop_reason": "error"
            }



        except openai.APIError as e:

            logger.error(
                "DeepSeek API error: %s",
                e
            )

            yield {
                "type": "error",
                "error": str(e)
            }

            yield {
                "type": "_turn_complete",
                "tool_calls": [],
                "stop_reason": "error"
            }



    def add_tool_results(
        self,
        messages: list[dict],
        tool_calls: list[dict],
        results: list[dict],
    ) -> list[dict]:

        assistant_msg = {

            "role": "assistant",

            "content": None,

            "tool_calls": [

                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(
                            tc.get("args", {})
                        ),
                    },
                }

                for tc in tool_calls
            ],
        }


        result_msgs = [

            {
                "role": "tool",
                "tool_call_id": r["tool_use_id"],
                "content": str(r["content"]),
            }

            for r in results
        ]


        return messages + [
            assistant_msg
        ] + result_msgs



    async def _fetch_models(self) -> list[str]:

        client = openai.AsyncOpenAI(
            **self._build_client_kwargs()
        )

        resp = await client.models.list()

        return [
            m.id
            for m in resp.data
        ]



    async def list_models(self) -> list[str]:

        try:

            return await self._fetch_models()

        except Exception:

            return DEEPSEEK_MODELS



    async def validate(self) -> bool:

        try:

            client = openai.OpenAI(
                **self._build_client_kwargs()
            )

            client.models.list()

            return True


        except Exception as e:

            logger.warning(
                "DeepSeek validation failed: %s",
                e
            )

            return False