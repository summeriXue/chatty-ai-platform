import asyncio
import json
import unittest
from pathlib import Path

import httpx

from run_tech_eval import (
    MAX_TOOL_RESULT_CHARS,
    build_metrics,
    parse_sse_data,
    run_read_only_case,
    sanitize_event_for_storage,
    run_write_case,
)

from fixtures import (
    restore_project_state,
    snapshot_project_state,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ParseSSEDataTests(unittest.TestCase):

    def test_parse_valid_sse_event(self):
        line = 'data: {"type":"text","text":"你好"}'

        event = parse_sse_data(line)

        self.assertEqual(
            event,
            {
                "type": "text",
                "text": "你好",
            },
        )

    def test_ignore_non_data_line(self):
        self.assertIsNone(parse_sse_data(""))

        self.assertIsNone(
            parse_sse_data("event: message")
        )

    def test_invalid_json_is_preserved(self):
        event = parse_sse_data(
            "data: not-valid-json"
        )

        self.assertEqual(
            event["type"],
            "_invalid_sse",
        )
        self.assertEqual(
            event["raw"],
            "not-valid-json",
        )


class StorageSanitizationTests(unittest.TestCase):

    def test_small_tool_result_is_unchanged(self):
        event = {
            "type": "tool_end",
            "tool": "read_file",
            "result": {
                "content": "small result",
            },
        }

        stored = sanitize_event_for_storage(
            event
        )

        self.assertEqual(stored, event)

    def test_large_tool_result_is_truncated(self):
        event = {
            "type": "tool_end",
            "tool": "read_file",
            "result": {
                "content": "x"
                * (MAX_TOOL_RESULT_CHARS + 100),
            },
        }

        stored = sanitize_event_for_storage(
            event
        )

        result = stored["result"]

        self.assertTrue(
            result["_truncated"]
        )
        self.assertGreater(
            result["original_chars"],
            MAX_TOOL_RESULT_CHARS,
        )
        self.assertEqual(
            len(result["preview"]),
            MAX_TOOL_RESULT_CHARS,
        )

    def test_sanitization_does_not_mutate_original_event(self):
        original_result = {
            "content": "x"
            * (MAX_TOOL_RESULT_CHARS + 100),
        }
        event = {
            "type": "tool_end",
            "result": original_result,
        }

        sanitize_event_for_storage(event)

        self.assertIs(
            event["result"],
            original_result,
        )
        self.assertNotIn(
            "_truncated",
            event["result"],
        )

    def test_non_tool_end_event_is_not_truncated(self):
        long_text = "x" * (
            MAX_TOOL_RESULT_CHARS + 100
        )
        event = {
            "type": "text",
            "text": long_text,
        }

        stored = sanitize_event_for_storage(
            event
        )

        self.assertEqual(
            stored["text"],
            long_text,
        )


class MetricsTests(unittest.TestCase):

    def test_build_metrics_from_normal_run(self):
        events = [
            {
                "type": "tool_args",
                "tool": "read_file",
                "args": {
                    "path": "example.py",
                },
            },
            {
                "type": "tool_end",
                "tool": "read_file",
                "result": {
                    "content": "example",
                },
            },
            {
                "type": "done",
                "model": "test-model",
            },
        ]

        metrics = build_metrics(events)

        self.assertEqual(
            metrics["tool_calls"],
            1,
        )
        self.assertEqual(
            metrics["tool_results"],
            1,
        )
        self.assertEqual(
            metrics["distinct_tools"],
            ["read_file"],
        )
        self.assertEqual(
            metrics["duplicate_tool_calls"],
            0,
        )
        self.assertFalse(
            metrics["max_iteration_hit"]
        )
        self.assertTrue(
            metrics["task_completed"]
        )

    def test_duplicate_tool_calls_are_counted(self):
        repeated_event = {
            "type": "tool_args",
            "tool": "read_file",
            "args": {
                "path": "example.py",
            },
        }

        events = [
            repeated_event,
            dict(repeated_event),
            {
                "type": "done",
                "model": "test-model",
            },
        ]

        metrics = build_metrics(events)

        self.assertEqual(
            metrics["tool_calls"],
            2,
        )
        self.assertEqual(
            metrics["duplicate_tool_calls"],
            1,
        )

    def test_max_iteration_error_is_detected(self):
        events = [
            {
                "type": "error",
                "error": (
                    "Tool loop exceeded "
                    "maximum iterations"
                ),
            }
        ]

        metrics = build_metrics(events)

        self.assertTrue(
            metrics["max_iteration_hit"]
        )
        self.assertFalse(
            metrics["task_completed"]
        )


class ReadOnlyRunnerTests(unittest.IsolatedAsyncioTestCase):

    async def test_run_read_only_case_from_mock_sse_stream(self):
        async def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            self.assertEqual(
                request.method,
                "POST",
            )
            self.assertEqual(
                request.url.path,
                "/api/agents/test-agent/chat",
            )
            self.assertEqual(
                request.headers["Authorization"],
                "Bearer test-token",
            )

            request_body = json.loads(
                request.content.decode("utf-8")
            )

            self.assertEqual(
                request_body["tool_mode"],
                "read-only",
            )
            self.assertEqual(
                request_body["messages"],
                [
                    {
                        "role": "user",
                        "content": "检查当前实现。",
                    }
                ],
            )

            sse = "\n".join(
                [
                    (
                        'data: {"type":"conversation_id",'
                        '"id":"conv-test-001"}'
                    ),
                    (
                        'data: {"type":"text",'
                        '"text":"我先检查相关代码。"}'
                    ),
                    (
                        'data: {"type":"tool_start",'
                        '"tool":"read_file",'
                        '"tool_use_id":"tool-1"}'
                    ),
                    (
                        'data: {"type":"tool_args",'
                        '"tool":"read_file",'
                        '"tool_use_id":"tool-1",'
                        '"args":{"path":"example.py"}}'
                    ),
                    (
                        'data: {"type":"tool_end",'
                        '"tool":"read_file",'
                        '"tool_use_id":"tool-1",'
                        '"result":{"content":"example"}}'
                    ),
                    (
                        'data: {"type":"text",'
                        '"text":"实现已经确认。"}'
                    ),
                    (
                        'data: {"type":"done",'
                        '"model":"test-model"}'
                    ),
                    "",
                ]
            )

            return httpx.Response(
                200,
                headers={
                    "Content-Type": "text/event-stream",
                },
                content=sse.encode("utf-8"),
            )

        transport = httpx.MockTransport(
            handler
        )

        case = {
            "id": "TECH-TEST-01",
            "category": "test",
            "mode": "read_only",
            "prompt": "检查当前实现。",
            "scoring": [
                "autonomous_investigation",
                "evidence_judgment",
                "convergence",
            ],
        }

        result = await run_read_only_case(
            case=case,
            agent_id="test-agent",
            base_url="http://testserver/api/agents",
            token="test-token",
            timeout_seconds=5.0,
            transport=transport,
        )

        self.assertEqual(
            result["run"]["status"],
            "completed",
        )
        self.assertEqual(
            result["run"]["model"],
            "test-model",
        )

        self.assertEqual(
            result["execution"]["conversation_id"],
            "conv-test-001",
        )
        self.assertEqual(
            result["execution"]["response_text"],
            "我先检查相关代码。实现已经确认。",
        )
        self.assertIsNone(
            result["execution"]["error"]
        )

        self.assertEqual(
            result["metrics"]["tool_calls"],
            1,
        )
        self.assertEqual(
            result["metrics"]["tool_results"],
            1,
        )
        self.assertEqual(
            result["metrics"]["distinct_tools"],
            ["read_file"],
        )
        self.assertEqual(
            result["metrics"]["duplicate_tool_calls"],
            0,
        )
        self.assertTrue(
            result["metrics"]["task_completed"]
        )

        events = (
            result["execution"]["phases"][0]["events"]
        )

        self.assertEqual(
            [event["type"] for event in events],
            [
                "conversation_id",
                "text",
                "tool_start",
                "tool_args",
                "tool_end",
                "text",
                "done",
            ],
        )

        self.assertEqual(
            result["evaluation"][
                "autonomous_investigation"
            ],
            None,
        )
        self.assertEqual(
            result["evaluation"][
                "requirement_understanding"
            ],
            "N/A",
        )

    async def test_run_read_only_case_recovers_model_after_hard_max(self):
        async def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            if request.method == "POST":
                self.assertEqual(
                    request.url.path,
                    "/api/agents/test-agent/chat",
                )
                self.assertEqual(
                    request.headers["Authorization"],
                    "Bearer test-token",
                )

                sse = "\n".join(
                    [
                        (
                            'data: {"type":"conversation_id",'
                            '"id":"conv-test-hard-max"}'
                        ),
                        (
                            'data: {"type":"text",'
                            '"text":"继续检查相关实现。"}'
                        ),
                        (
                            'data: {"type":"error",'
                            '"error":"Tool loop exceeded maximum iterations"}'
                        ),
                        "",
                    ]
                )

                return httpx.Response(
                    200,
                    headers={
                        "Content-Type": "text/event-stream",
                    },
                    content=sse.encode("utf-8"),
                )

            if request.method == "GET":
                self.assertEqual(
                    request.url.path,
                    (
                        "/api/agents/test-agent/"
                        "conversations/conv-test-hard-max"
                    ),
                )
                self.assertEqual(
                    request.headers["Authorization"],
                    "Bearer test-token",
                )

                return httpx.Response(
                    200,
                    json={
                        "id": "conv-test-hard-max",
                        "last_model": None,
                        "messages": [
                            {
                                "role": "user",
                                "content": "检查这个间歇性停止问题。",
                                "model": "",
                            },
                            {
                                "role": "assistant",
                                "content": "继续检查相关实现。",
                                "model": "deepseek-v4-flash",
                            },
                        ],
                    },
                )

            self.fail(
                f"Unexpected request: {request.method} {request.url}"
            )

        transport = httpx.MockTransport(
            handler
        )

        case = {
            "id": "TECH-TEST-HARD-MAX",
            "category": "test",
            "mode": "read_only",
            "prompt": "检查这个间歇性停止问题。",
            "scoring": [
                "autonomous_investigation",
                "evidence_judgment",
                "convergence",
            ],
        }

        result = await run_read_only_case(
            case=case,
            agent_id="test-agent",
            base_url="http://testserver/api/agents",
            token="test-token",
            timeout_seconds=5.0,
            transport=transport,
        )

        self.assertEqual(
            result["run"]["status"],
            "error",
        )
        self.assertEqual(
            result["run"]["model"],
            "deepseek-v4-flash",
        )

        self.assertEqual(
            result["execution"]["conversation_id"],
            "conv-test-hard-max",
        )
        self.assertEqual(
            result["execution"]["response_text"],
            "继续检查相关实现。",
        )
        self.assertEqual(
            result["execution"]["error"],
            "Tool loop exceeded maximum iterations",
        )

        self.assertTrue(
            result["metrics"]["max_iteration_hit"]
        )
        self.assertFalse(
            result["metrics"]["task_completed"]
        )

    def test_run_write_case_approves_and_continues(self):
        case = {
            "id": "TECH-WRITE-TEST",
            "mode": "write",
            "prompt": "Update one project file.",
            "evaluation": {},
        }

        request_count = {
            "chat": 0,
            "execute": 0,
        }

        async def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path

            if path.endswith("/chat"):
                request_count["chat"] += 1

                if request_count["chat"] == 1:
                    body = json.loads(request.content.decode())

                    self.assertEqual(body["tool_mode"], "normal")
                    self.assertEqual(
                        body["messages"],
                        [
                            {
                                "role": "user",
                                "content": "Update one project file.",
                            }
                        ],
                    )
                    self.assertNotIn("approved_tool", body)

                    return httpx.Response(
                        200,
                        text=(
                            'data: {"type":"conversation_id","id":"conv-1"}\n\n'
                            'data: {"type":"text","text":"I will update the file."}\n\n'
                            'data: {"type":"confirm","tool":"write_project_file",'
                            '"args":{"path":"README.md","content":"updated"},'
                            '"tool_use_id":"tool-1","msg_id":"msg-1"}\n\n'
                        ),
                        headers={"Content-Type": "text/event-stream"},
                    )

                body = json.loads(request.content.decode())

                self.assertEqual(body["conversation_id"], "conv-1")
                self.assertEqual(body["tool_mode"], "normal")
                self.assertEqual(
                    body["messages"],
                    [
                        {
                            "role": "user",
                            "content": "[Approved] write_project_file",
                        }
                    ],
                )
                self.assertEqual(
                    body["approved_tool"],
                    {
                        "tool": "write_project_file",
                        "args": {
                            "path": "README.md",
                            "content": "updated",
                        },
                        "toolUseId": "tool-1",
                        "msgId": "msg-1",
                        "result": {
                            "ok": True,
                            "path": "README.md",
                        },
                    },
                )

                return httpx.Response(
                    200,
                    text=(
                        'data: {"type":"conversation_id","id":"conv-1"}\n\n'
                        'data: {"type":"text","text":"The file has been updated."}\n\n'
                        'data: {"type":"done","model":"deepseek-v4-flash"}\n\n'
                    ),
                    headers={"Content-Type": "text/event-stream"},
                )

            if path.endswith("/tool/execute"):
                request_count["execute"] += 1

                body = json.loads(request.content.decode())

                self.assertEqual(
                    body,
                    {
                        "tool": "write_project_file",
                        "args": {
                            "path": "README.md",
                            "content": "updated",
                        },
                        "tool_use_id": "tool-1",
                        "msg_id": "msg-1",
                        "conversation_id": "conv-1",
                    },
                )

                return httpx.Response(
                    200,
                    json={
                        "ok": True,
                        "path": "README.md",
                    },
                )

            raise AssertionError(f"Unexpected request: {request.method} {path}")

        async def run_test():
            result = await run_write_case(
                case=case,
                agent_id="agent-1",
                base_url="http://localhost:8000/api/agents",
                token="test-token",
                timeout_seconds=5.0,
                transport=httpx.MockTransport(handler),
            )

            self.assertEqual(result["run"]["status"], "completed")
            self.assertEqual(result["run"]["model"], "deepseek-v4-flash")
            self.assertEqual(
                result["execution"]["conversation_id"],
                "conv-1",
            )
            self.assertEqual(
                result["execution"]["response_text"],
                "I will update the file.The file has been updated.",
            )
            self.assertIsNone(result["execution"]["error"])

            self.assertEqual(request_count["chat"], 2)
            self.assertEqual(request_count["execute"], 1)

            self.assertEqual(result["metrics"]["approval_count"], 1)
            self.assertEqual(result["metrics"]["continuation_count"], 1)
            self.assertTrue(result["metrics"]["task_completed"])

            self.assertEqual(
                [phase["kind"] for phase in result["execution"]["phases"]],
                [
                    "chat",
                    "tool_execute",
                    "chat",
                ],
            )

        asyncio.run(run_test())

    def test_project_state_snapshot_restores_dirty_and_new_files(self):
        existing_path = PROJECT_ROOT / "evals" / "_snapshot_existing_test.txt"
        new_path = PROJECT_ROOT / "evals" / "_snapshot_new_test.txt"

        original_content = "before eval\n"

        existing_path.write_text(
            original_content,
            encoding="utf-8",
        )

        snapshot = snapshot_project_state()

        try:
            existing_path.write_text(
                "changed by eval\n",
                encoding="utf-8",
            )

            new_path.write_text(
                "created by eval\n",
                encoding="utf-8",
            )

            restore_project_state(snapshot)

            self.assertTrue(existing_path.exists())
            self.assertEqual(
                existing_path.read_text(encoding="utf-8"),
                original_content,
            )

            self.assertFalse(new_path.exists())

        finally:
            if snapshot.backup_dir.exists():
                restore_project_state(snapshot)

            existing_path.unlink(missing_ok=True)
            new_path.unlink(missing_ok=True)

if __name__ == "__main__":
    unittest.main()
