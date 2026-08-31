"""Run Chatty Tech Agent eval cases.

Eval v1 intentionally supports read-only cases only.

The runner stays outside the Chatty runtime and observes the existing
/api/agents/{agent_id}/chat SSE contract without adding eval-specific
instrumentation to the runtime.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from fixtures import (
    create_tech_eval_agent,
    restore_project_state,
    snapshot_project_state,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES_FILE = PROJECT_ROOT / "evals" / "cases" / "tech_cases.json"
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "evals" / "results"
DEFAULT_BASE_URL = "http://localhost:8000/api/agents"

MAX_TOOL_RESULT_CHARS = 10_000
MAX_APPROVALS = 10
MAX_PHASES = 20


def load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Cases file must contain a JSON array.")

    return data


def find_case(cases: list[dict[str, Any]], case_id: str) -> dict[str, Any]:
    for case in cases:
        if case.get("id") == case_id:
            return case
    raise ValueError(f"Case not found: {case_id}")


def parse_sse_data(line: str) -> dict[str, Any] | None:
    if not line.startswith("data:"):
        return None

    payload = line[5:].strip()
    if not payload:
        return None

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        return {
            "type": "_invalid_sse",
            "raw": payload,
        }

    if isinstance(event, dict):
        return event

    return {
        "type": "_invalid_sse",
        "raw": event,
    }


def normalized_tool_key(event: dict[str, Any]) -> str:
    tool = event.get("tool", "")
    args = event.get("args", {})
    try:
        args_text = json.dumps(
            args,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    except TypeError:
        args_text = repr(args)
    return f"{tool}:{args_text}"


def sanitize_event_for_storage(event: dict[str, Any]) -> dict[str, Any]:
    """Trim very large tool results before writing the eval artifact.

    Runtime observation still uses the original full SSE event. This function
    affects only the JSON persisted under evals/results/.
    """
    stored = dict(event)

    if stored.get("type") != "tool_end" or "result" not in stored:
        return stored

    result = stored["result"]

    try:
        serialized = json.dumps(
            result,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        serialized = repr(result)

    if len(serialized) <= MAX_TOOL_RESULT_CHARS:
        return stored

    stored["result"] = {
        "_truncated": True,
        "original_chars": len(serialized),
        "preview": serialized[:MAX_TOOL_RESULT_CHARS],
    }

    return stored


def build_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    tool_args_events = [e for e in events if e.get("type") == "tool_args"]
    tool_end_events = [e for e in events if e.get("type") == "tool_end"]
    confirm_events = [e for e in events if e.get("type") == "confirm"]
    done_events = [e for e in events if e.get("type") == "done"]
    error_events = [e for e in events if e.get("type") == "error"]

    tool_keys = [normalized_tool_key(e) for e in tool_args_events]
    counts = Counter(tool_keys)
    duplicate_tool_calls = sum(count - 1 for count in counts.values() if count > 1)

    tool_names = [
        e.get("tool")
        for e in tool_args_events
        if e.get("tool")
    ]

    max_iteration_hit = any(
        "maximum iterations" in str(e.get("error", "")).lower()
        for e in error_events
    )

    return {
        "tool_calls": len(tool_args_events),
        "tool_results": len(tool_end_events),
        "distinct_tools": sorted(set(tool_names)),
        "duplicate_tool_calls": duplicate_tool_calls,
        "approval_count": len(confirm_events),
        "continuation_count": 0,
        "max_iteration_hit": max_iteration_hit,
        "task_completed": bool(done_events) and not error_events,
        # These are intentionally left unknown in v1 rather than guessed.
        "read_calls": None,
        "write_calls": None,
        "validation_calls": None,
        "iterations": None,
    }


def build_evaluation(case: dict[str, Any]) -> dict[str, Any]:
    dimensions = {
        "requirement_understanding": None,
        "clarification_judgment": None,
        "autonomous_investigation": None,
        "evidence_judgment": None,
        "change_decision": None,
        "validation": None,
        "convergence": None,
        "language_consistency": None,
        "notes": "",
    }

    applicable = set(case.get("scoring", []))
    for name in list(dimensions):
        if name in {"language_consistency", "notes"}:
            continue
        if name not in applicable:
            dimensions[name] = "N/A"

    return dimensions

async def _run_chat_phase(
    *,
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    request_body: dict[str, Any],
) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    response_text_parts: list[str] = []
    conversation_id: str | None = None
    model: str | None = None
    error: str | None = None
    confirm: dict[str, Any] | None = None
    done = False

    async with client.stream(
        "POST",
        url,
        headers=headers,
        json=request_body,
    ) as response:
        response.raise_for_status()

        async for line in response.aiter_lines():
            event = parse_sse_data(line)
            if event is None:
                continue

            events.append(event)
            event_type = event.get("type")

            if event_type == "conversation_id":
                conversation_id = event.get("id") or conversation_id

            elif event_type == "text":
                response_text_parts.append(str(event.get("text", "")))

            elif event_type == "confirm":
                confirm = event

            elif event_type == "done":
                model = event.get("model") or model
                done = True

            elif event_type == "error":
                error = str(event.get("error", "Unknown error"))

    return {
        "events": events,
        "response_text": "".join(response_text_parts),
        "conversation_id": conversation_id,
        "model": model,
        "error": error,
        "confirm": confirm,
        "done": done,
    }

async def run_read_only_case(
    *,
    case: dict[str, Any],
    agent_id: str,
    base_url: str,
    token: str,
    timeout_seconds: float,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    case_id = case["id"]

    if case.get("mode") != "read_only":
        raise ValueError(
            f"{case_id} uses mode={case.get('mode')!r}. "
            "Eval runner v1 supports read_only cases only."
        )

    started_at = datetime.now(timezone.utc)
    events: list[dict[str, Any]] = []
    response_text_parts: list[str] = []
    conversation_id: str | None = None
    model: str | None = None
    error: str | None = None

    request_body = {
        "messages": [
            {
                "role": "user",
                "content": case["prompt"],
            }
        ],
        "tool_mode": "read-only",
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }

    url = f"{base_url.rstrip('/')}/{agent_id}/chat"

    async with httpx.AsyncClient(
        timeout=timeout_seconds,
        transport=transport,
    ) as client:
        async with client.stream(
            "POST",
            url,
            headers=headers,
            json=request_body,
        ) as response:

            async for line in response.aiter_lines():
                event = parse_sse_data(line)
                if event is None:
                    continue

                events.append(event)
                event_type = event.get("type")

                if event_type == "conversation_id":
                    conversation_id = event.get("id") or conversation_id

                elif event_type == "text":
                    response_text_parts.append(str(event.get("text", "")))

                elif event_type == "done":
                    model = event.get("model") or model

                elif event_type == "error":
                    error = str(event.get("error", "Unknown error"))

        if model is None and conversation_id:
            conversation_response = await client.get(
                f"{base_url.rstrip('/')}/{agent_id}/conversations/{conversation_id}",
                headers=headers,
            )

            if conversation_response.status_code == 200:
                conversation = conversation_response.json()

                model = conversation.get("last_model") or model

                if model is None:
                    for message in reversed(conversation.get("messages", [])):
                        message_model = message.get("model")
                        if message_model:
                            model = message_model
                            break

    finished_at = datetime.now(timezone.utc)
    final_response = "".join(response_text_parts)
    metrics = build_metrics(events)

    status = "completed" if metrics["task_completed"] else "error"
    if error is None and status == "error":
        error = "SSE stream ended without a done event."

    return {
        "schema_version": 1,
        "run": {
            "case_id": case_id,
            "agent": "tech",
            "agent_id": agent_id,
            "model": model,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "status": status,
        },
        "execution": {
            "conversation_id": conversation_id,
            "phases": [
                {
                    "index": 1,
                    "kind": "chat",
                    "request": {
                        "tool_mode": "read-only",
                    },
                    "events": [
                        sanitize_event_for_storage(event)
                        for event in events
                    ],
                }
            ],
            "response_text": final_response,
            "error": error,
        },
        "metrics": metrics,
        "evaluation": build_evaluation(case),
    }

async def run_write_case(
    *,
    case: dict[str, Any],
    agent_id: str,
    base_url: str,
    token: str,
    timeout_seconds: float,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    case_id = case["id"]

    if case.get("mode") != "write":
        raise ValueError(
            f"{case_id} uses mode={case.get('mode')!r}. "
            "run_write_case requires mode='write'."
        )

    # Real write evals may modify the shared project working tree.
    # MockTransport tests do not execute real project tools, so they do not
    # need filesystem isolation.
    project_snapshot = (
        snapshot_project_state()
        if transport is None
        else None
    )

    try:
        started_at = datetime.now(timezone.utc)

        all_events: list[dict[str, Any]] = []
        response_text_parts: list[str] = []
        phases: list[dict[str, Any]] = []

        conversation_id: str | None = None
        model: str | None = None
        error: str | None = None

        approval_count = 0

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        }

        base_agent_url = f"{base_url.rstrip('/')}/{agent_id}"
        chat_url = f"{base_agent_url}/chat"
        execute_url = f"{base_agent_url}/tool/execute"

        request_body: dict[str, Any] = {
            "messages": [
                {
                    "role": "user",
                    "content": case["prompt"],
                }
            ],
            "tool_mode": "normal",
        }

        async with httpx.AsyncClient(
            timeout=timeout_seconds,
            transport=transport,
        ) as client:
            for phase_index in range(1, MAX_PHASES + 1):
                phase = await _run_chat_phase(
                    client=client,
                    url=chat_url,
                    headers=headers,
                    request_body=request_body,
                )

                phase_events = phase["events"]
                all_events.extend(phase_events)

                if phase["response_text"]:
                    response_text_parts.append(phase["response_text"])

                conversation_id = (
                    phase["conversation_id"]
                    or conversation_id
                )
                model = phase["model"] or model

                phases.append(
                    {
                        "index": len(phases) + 1,
                        "kind": "chat",
                        "request": {
                            "tool_mode": request_body.get("tool_mode"),
                            "approved_tool": bool(
                                request_body.get("approved_tool")
                            ),
                        },
                        "events": [
                            sanitize_event_for_storage(event)
                            for event in phase_events
                        ],
                    }
                )

                if phase["error"]:
                    error = phase["error"]
                    break

                confirm = phase["confirm"]

                if confirm is None:
                    if phase["done"]:
                        break

                    error = "SSE stream ended without a done or confirm event."
                    break

                approval_count += 1

                if approval_count > MAX_APPROVALS:
                    error = (
                        "Eval runner exceeded maximum approval count "
                        f"({MAX_APPROVALS})."
                    )
                    break

                tool = str(confirm.get("tool", ""))
                args = confirm.get("args") or {}
                tool_use_id = str(confirm.get("tool_use_id", ""))
                msg_id = str(confirm.get("msg_id", ""))

                execute_body = {
                    "tool": tool,
                    "args": args,
                    "tool_use_id": tool_use_id,
                    "msg_id": msg_id,
                    "conversation_id": conversation_id,
                }

                execute_response = await client.post(
                    execute_url,
                    headers=headers,
                    json=execute_body,
                )

                execute_phase: dict[str, Any] = {
                    "index": len(phases) + 1,
                    "kind": "tool_execute",
                    "request": {
                        "tool": tool,
                        "args": args,
                        "tool_use_id": tool_use_id,
                        "msg_id": msg_id,
                        "conversation_id": conversation_id,
                    },
                    "status_code": execute_response.status_code,
                }

                if execute_response.is_success:
                    result = execute_response.json()
                    execute_phase["result"] = sanitize_event_for_storage(
                        {
                            "type": "tool_end",
                            "tool": tool,
                            "tool_use_id": tool_use_id,
                            "result": result,
                        }
                    ).get("result")
                else:
                    try:
                        failure_detail: Any = execute_response.json()
                    except ValueError:
                        failure_detail = execute_response.text

                    execute_phase["error"] = failure_detail
                    phases.append(execute_phase)

                    error = (
                        f"Approved tool execution failed "
                        f"({execute_response.status_code}): "
                        f"{failure_detail}"
                    )
                    break

                phases.append(execute_phase)

                approved_tool = {
                    "tool": tool,
                    "args": args,
                    "toolUseId": tool_use_id,
                    "msgId": msg_id,
                    "result": result,
                }

                request_body = {
                    "messages": [
                        {
                            "role": "user",
                            "content": f"[Approved] {tool}",
                        }
                    ],
                    "conversation_id": conversation_id,
                    "tool_mode": "normal",
                    "approved_tool": approved_tool,
                }

            else:
                error = (
                    "Eval runner exceeded maximum phase count "
                    f"({MAX_PHASES})."
                )

            if model is None and conversation_id:
                conversation_response = await client.get(
                    f"{base_agent_url}/conversations/{conversation_id}",
                    headers=headers,
                )

                if conversation_response.status_code == 200:
                    conversation = conversation_response.json()

                    model = conversation.get("last_model") or model

                    if model is None:
                        for message in reversed(
                            conversation.get("messages", [])
                        ):
                            message_model = message.get("model")
                            if message_model:
                                model = message_model
                                break

        finished_at = datetime.now(timezone.utc)
        final_response = "".join(response_text_parts)

        metrics = build_metrics(all_events)
        metrics["approval_count"] = approval_count
        metrics["continuation_count"] = max(0, approval_count)

        status = (
            "completed"
            if metrics["task_completed"] and error is None
            else "error"
        )

        if error is None and status == "error":
            error = "Write Eval ended without successful completion."

        return {
            "schema_version": 1,
            "run": {
                "case_id": case_id,
                "agent": "tech",
                "agent_id": agent_id,
                "model": model,
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "status": status,
            },
            "execution": {
                "conversation_id": conversation_id,
                "phases": phases,
                "response_text": final_response,
                "error": error,
            },
            "metrics": metrics,
            "evaluation": build_evaluation(case),
        }

    finally:
        if project_snapshot is not None:
            restore_project_state(project_snapshot)

def result_filename(result: dict[str, Any]) -> str:
    case_id = result["run"]["case_id"]
    model = result["run"].get("model") or "unknown-model"
    model = "".join(c if c.isalnum() or c in "-_." else "_" for c in model)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{stamp}_{model}_{case_id}.json"


def save_result(result: dict[str, Any], results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / result_filename(result)

    with path.open("w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
        )
        f.write("\n")

    return path


async def delete_eval_agent_via_api(
    *,
    base_url: str,
    agent_id: str,
    token: str,
    timeout_seconds: float,
) -> None:
    """Delete a temporary Eval Agent through the running Chatty backend."""
    headers = {
        "Authorization": f"Bearer {token}",
    }

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.delete(
            f"{base_url}/{agent_id}",
            headers=headers,
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to delete temporary Eval Agent "
            f"({response.status_code}): {response.text}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Chatty Tech Agent eval cases."
    )
    parser.add_argument(
        "--case",
        dest="case_id",
        help="Case ID to run, for example TECH-REQ-01.",
    )
    parser.add_argument(
        "--list-cases",
        action="store_true",
        help="List available cases without calling Chatty.",
    )
    parser.add_argument(
        "--agent-id",
        help=(
            "Existing Tech Agent database ID. "
            "If omitted, a temporary isolated Tech Eval Agent is created."
        ),
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Agents API base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("CHATTY_TOKEN"),
        help="Bearer token. Defaults to CHATTY_TOKEN environment variable.",
    )
    parser.add_argument(
        "--cases-file",
        type=Path,
        default=DEFAULT_CASES_FILE,
        help=f"Cases JSON file. Default: {DEFAULT_CASES_FILE}",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help=f"Results directory. Default: {DEFAULT_RESULTS_DIR}",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="HTTP timeout in seconds. Default: 300.",
    )
    return parser


async def async_main(args: argparse.Namespace) -> int:
    cases = load_cases(args.cases_file)

    if args.list_cases:
        for case in cases:
            print(
                f"{case.get('id', '<missing-id>'):18} "
                f"{case.get('mode', '<missing-mode>'):10} "
                f"{case.get('category', '')}"
            )
        return 0

    if not args.case_id:
        raise SystemExit("--case is required unless --list-cases is used.")

    if not args.token:
        raise SystemExit(
            "No bearer token provided. Use --token or set CHATTY_TOKEN."
        )

    case = find_case(cases, args.case_id)

    temporary_agent: dict[str, Any] | None = None

    try:
        if args.agent_id:
            agent_id = args.agent_id
        else:
            temporary_agent = create_tech_eval_agent(case["id"])
            agent_id = temporary_agent["id"]
            print(
                f"Created temporary Eval Agent: "
                f"{temporary_agent['slug']} ({agent_id})"
            )

        print(f"Running {case['id']} ({case.get('mode')})...")

        if case.get("mode") == "read_only":
            result = await run_read_only_case(
                case=case,
                agent_id=agent_id,
                base_url=args.base_url,
                token=args.token,
                timeout_seconds=args.timeout,
            )
        elif case.get("mode") == "write":
            result = await run_write_case(
                case=case,
                agent_id=agent_id,
                base_url=args.base_url,
                token=args.token,
                timeout_seconds=args.timeout,
            )
        else:
            raise ValueError(
                f"Unsupported Eval mode: {case.get('mode')!r}"
            )

        path = save_result(result, args.results_dir)

    finally:
        if temporary_agent:
            try:
                await delete_eval_agent_via_api(
                    base_url=args.base_url,
                    agent_id=temporary_agent["id"],
                    token=args.token,
                    timeout_seconds=args.timeout,
                )
                print(
                    f"Deleted temporary Eval Agent: "
                    f"{temporary_agent['slug']} ({temporary_agent['id']})"
                )
            except Exception as cleanup_error:
                print(
                    f"WARNING: Failed to delete temporary Eval Agent "
                    f"{temporary_agent['slug']} "
                    f"({temporary_agent['id']}): {cleanup_error}"
                )

    print(f"Status: {result['run']['status']}")
    print(f"Model: {result['run'].get('model')}")
    print(f"Tool calls: {result['metrics']['tool_calls']}")
    print(f"Result: {path}")

    if result["execution"]["error"]:
        print(f"Error: {result['execution']['error']}")
        return 1

    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
