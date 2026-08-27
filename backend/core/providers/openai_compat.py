"""
Chatty — Shared helpers for OpenAI-compatible providers.

Used by providers such as DeepSeek and Ollama that expose an
OpenAI-compatible chat completions API. Streaming, tool calling,
message formatting, and tool result handling are centralized here
to avoid duplication.
"""

import json
import logging
from typing import AsyncGenerator

import openai

from core.providers.base import AIProvider

logger = logging.getLogger(__name__)

class OpenAICompatibleProvider(AIProvider):

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
    ):
        super().__init__(model=model)
        self.api_key = api_key
        self.base_url = base_url

    def _create_client(self):
        return openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def _ensure_array_items(self, schema: dict) -> dict:
        """Recursively ensure all array types have an items field (OpenAI requirement)."""
        if not isinstance(schema, dict):
            return schema
        result = dict(schema)
        if result.get("type") == "array" and "items" not in result:
            result["items"] = {}
        if "properties" in result:
            result["properties"] = {
                k: self._ensure_array_items(v) for k, v in result["properties"].items()
            }
        if "items" in result and isinstance(result["items"], dict):
            result["items"] = self._ensure_array_items(result["items"])
        return result

    def _format_tools(self, tools: list[dict]) -> list[dict]:
        """Convert internal tool format to OpenAI function calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": self._ensure_array_items(
                        t.get(
                            "input_schema",
                            {"type": "object", "properties": {}}
                        )
                    ),
                },
            }
            for t in tools
        ]

    def _build_messages(
        self,
        messages: list[dict],
        system_prompt: str | tuple[str, str],
    ) -> list[dict]:
        """Build OpenAI-format message list with system prompt prepended."""

        # Join static + volatile prompt if tuple
        # (prompt caching is provider-specific)
        if isinstance(system_prompt, tuple):
            system_prompt = "\n".join(system_prompt)

        api_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            role = m.get("role")
            if role == "user":
                api_messages.append({"role": "user", "content": m.get("content", "")})
            elif role == "assistant":
                msg: dict = {"role": "assistant"}
                if m.get("content") is not None:
                    msg["content"] = m["content"]
                if m.get("tool_calls"):
                    msg["tool_calls"] = m["tool_calls"]
                api_messages.append(msg)
            elif role == "tool":
                api_messages.append({
                    "role": "tool",
                    "tool_call_id": m.get("tool_call_id", ""),
                    "content": m.get("content", ""),
                })
        return api_messages

    async def stream_turn(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: str | tuple[str, str],
        max_tokens: int = 8192,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream one LLM turn using the OpenAI-compatible chat completions API.

        Yields event dicts: text, tool_start, tool_args, _turn_complete, error.
        """

        client = self._create_client()
        openai_tools = self._format_tools(tools)
        api_messages = self._build_messages(messages, system_prompt)

        logger.debug(
            "OpenAI-compatible request: provider=%s messages=%d tools=%d",
            self.provider_name,
            len(api_messages),
            len(openai_tools),
        )

        tool_calls: list[dict] = []

        try:
            kwargs: dict = {
                "model": self.model,
                "messages": api_messages,
                "stream": True,
                "max_tokens": max_tokens,
            }

            if openai_tools:
                kwargs["tools"] = openai_tools
                kwargs["tool_choice"] = "auto"

            if self.provider_name == "deepseek":
                kwargs["extra_body"] = {
                    "thinking": {
                        "type": "disabled",
                    },
                }

            if self.provider_name == "ollama":
                kwargs["extra_body"] = {"think": False}

            try:
                stream = await client.chat.completions.create(**kwargs)

            except Exception as e:
                logger.error("OpenAI compatible request failed: %s", e)
                raise

            finish_reason = None

            async for chunk in stream:
                if chunk.choices:
                    choice = chunk.choices[0]
                    delta = choice.delta

                    if choice.finish_reason:
                        finish_reason = choice.finish_reason

                else:
                    delta = None

                if not delta:
                    continue

                # Text content
                if delta.content:
                    yield {"type": "text", "text": delta.content}

                # Tool call streaming
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        while len(tool_calls) <= idx:
                            tool_calls.append({"id": "", "name": "", "input_json": ""})

                        if tc_delta.id:
                            tool_calls[idx]["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tool_calls[idx]["name"] = tc_delta.function.name
                                yield {
                                    "type": "tool_start",
                                    "tool": tc_delta.function.name,
                                    "tool_use_id": tool_calls[idx]["id"],
                                }
                            if tc_delta.function.arguments:
                                tool_calls[idx]["input_json"] += tc_delta.function.arguments

            # Parse accumulated tool args
            for tc in tool_calls:
                input_json = tc.get("input_json", "")

                if input_json:
                    try:
                        args = json.loads(input_json)
                    except Exception:
                        args = {}
                else:
                    # Valid no-argument tool call, e.g. git_project_status()
                    args = {}

                tc["args"] = args

                yield {
                    "type": "tool_args",
                    "tool": tc["name"],
                    "tool_use_id": tc["id"],
                    "args": args,
                }

            if tool_calls:
                stop_reason = "tool_use"
            elif finish_reason == "length":
                stop_reason = "length"
            else:
                stop_reason = "stop"

            yield {
                "type": "_turn_complete",
                "tool_calls": tool_calls,
                "stop_reason": stop_reason,
            }

        except openai.APIConnectionError:
            yield {"type": "error", "error": "connection_error"}
            yield {"type": "_turn_complete", "tool_calls": [], "stop_reason": "error"}
            return

        except openai.RateLimitError:
            yield {"type": "error", "error": "Rate-limited. Please try again in a moment."}
            yield {"type": "_turn_complete", "tool_calls": [], "stop_reason": "error"}
            return

        except openai.APIError as e:
            logger.error("OpenAI-compat API error: %s", e)
            yield {"type": "error", "error": f"AI service error: {str(e)}"}
            yield {
                "type": "_turn_complete",
                "tool_calls": [],
                "stop_reason": "error",
            }
            return

        except Exception as e:
            logger.exception(
                "Unexpected OpenAI-compatible provider error: %s",
                e,
            )
            yield {
                "type": "error",
                "error": "Unexpected AI provider error.",
            }
            yield {
                "type": "_turn_complete",
                "tool_calls": [],
                "stop_reason": "error",
            }
            return

    def add_tool_results(
        self,
        messages: list[dict],
        tool_calls: list[dict],
        results: list[dict],
    ) -> list[dict]:
        """Append assistant tool_calls message + tool result messages (OpenAI format)."""
        assistant_msg = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc.get("args", {})),
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

        return messages + [assistant_msg] + result_msgs

    @property
    def provider_name(self) -> str:
        raise NotImplementedError("Subclass must implement provider_name")

    async def list_models(self) -> list[str]:
        raise NotImplementedError

    async def validate(self) -> bool:
        raise NotImplementedError
