import logging

import httpx

from integrations.github.client import get_client


logger = logging.getLogger(__name__)


async def _github_get_repository(
    owner: str,
    repo: str,
) -> dict:
    client = get_client()

    if not client:
        return {"error": "GitHub not configured"}

    try:
        data = await client.get(f"/repos/{owner}/{repo}")

        return {
            "repository": {
                "name": data.get("name"),
                "full_name": data.get("full_name"),
                "description": data.get("description"),
                "private": data.get("private"),
                "default_branch": data.get("default_branch"),
                "language": data.get("language"),
                "stars": data.get("stargazers_count"),
                "forks": data.get("forks_count"),
                "open_issues": data.get("open_issues_count"),
                "html_url": data.get("html_url"),
            }
        }

    except httpx.HTTPStatusError as e:
        logger.error("github_get_repository error: %s", e)
        return {
            "error": f"GitHub API returned {e.response.status_code}",
        }

    except Exception as e:
        logger.error("github_get_repository error: %s", e)
        return {"error": str(e)}


async def _github_list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    limit: int = 20,
) -> dict:
    client = get_client()

    if not client:
        return {"error": "GitHub not configured"}

    limit = max(1, min(limit, 100))

    try:
        data = await client.get(
            f"/repos/{owner}/{repo}/issues",
            params={
                "state": state,
                "per_page": limit,
            },
        )

        issues = []

        for item in data:
            # GitHub's /issues endpoint also returns pull requests.
            if "pull_request" in item:
                continue

            issues.append({
                "number": item.get("number"),
                "title": item.get("title"),
                "state": item.get("state"),
                "user": (item.get("user") or {}).get("login"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "html_url": item.get("html_url"),
            })

        return {
            "issues": issues,
            "count": len(issues),
        }

    except httpx.HTTPStatusError as e:
        logger.error("github_list_issues error: %s", e)
        return {
            "error": f"GitHub API returned {e.response.status_code}",
        }

    except Exception as e:
        logger.error("github_list_issues error: %s", e)
        return {"error": str(e)}


async def _github_get_issue(
    owner: str,
    repo: str,
    issue_number: int,
) -> dict:
    client = get_client()

    if not client:
        return {"error": "GitHub not configured"}

    try:
        data = await client.get(
            f"/repos/{owner}/{repo}/issues/{issue_number}"
        )

        return {
            "issue": {
                "number": data.get("number"),
                "title": data.get("title"),
                "body": data.get("body"),
                "state": data.get("state"),
                "user": (data.get("user") or {}).get("login"),
                "labels": [
                    label.get("name")
                    for label in data.get("labels", [])
                ],
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "html_url": data.get("html_url"),
            }
        }

    except httpx.HTTPStatusError as e:
        logger.error("github_get_issue error: %s", e)
        return {
            "error": f"GitHub API returned {e.response.status_code}",
        }

    except Exception as e:
        logger.error("github_get_issue error: %s", e)
        return {"error": str(e)}
    
async def _github_create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
) -> dict:
    client = get_client()

    if not client:
        return {"error": "GitHub not configured"}

    try:
        data = await client.post(
            f"/repos/{owner}/{repo}/issues",
            json={
                "title": title,
                "body": body,
            },
        )

        return {
            "ok": True,
            "issue": {
                "number": data.get("number"),
                "title": data.get("title"),
                "state": data.get("state"),
                "html_url": data.get("html_url"),
                "created_at": data.get("created_at"),
            },
        }

    except httpx.HTTPStatusError as e:
        logger.error("github_create_issue error: %s", e)
        return {
            "error": f"GitHub API returned {e.response.status_code}",
        }

    except Exception as e:
        logger.error("github_create_issue error: %s", e)
        return {"error": str(e)}

# ── Tool definitions ──────────────────────────────────────────────────────

GITHUB_TOOL_DEFS = [
    {
        "name": "github_get_repository",
        "description": (
            "Get metadata for a GitHub repository. "
            "Use this to inspect repository information such as description, "
            "default branch, language, stars, forks, and open issue count."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "GitHub repository owner or organization.",
                },
                "repo": {
                    "type": "string",
                    "description": "GitHub repository name.",
                },
            },
            "required": ["owner", "repo"],
        },
        "kind": "integration",
    },
    {
        "name": "github_list_issues",
        "description": (
            "List issues in a GitHub repository. "
            "Pull requests returned by GitHub's issues endpoint are excluded."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "GitHub repository owner or organization.",
                },
                "repo": {
                    "type": "string",
                    "description": "GitHub repository name.",
                },
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Issue state. Defaults to open.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum issues to return. Defaults to 20, max 100.",
                },
            },
            "required": ["owner", "repo"],
        },
        "kind": "integration",
    },
    {
        "name": "github_get_issue",
        "description": (
            "Read a single GitHub issue including its title, body, labels, "
            "state, author, and timestamps."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "GitHub repository owner or organization.",
                },
                "repo": {
                    "type": "string",
                    "description": "GitHub repository name.",
                },
                "issue_number": {
                    "type": "integer",
                    "description": "GitHub issue number.",
                },
            },
            "required": ["owner", "repo", "issue_number"],
        },
        "kind": "integration",
    },
    {
        "name": "github_create_issue",
        "description": (
            "Create a new issue in a GitHub repository. "
            "Use this when the user explicitly wants a tracked GitHub issue created. "
            "This modifies the remote repository and requires user approval."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "GitHub repository owner or organization.",
                },
                "repo": {
                    "type": "string",
                    "description": "GitHub repository name.",
                },
                "title": {
                    "type": "string",
                    "description": "Issue title.",
                },
                "body": {
                    "type": "string",
                    "description": "Issue body in Markdown.",
                },
            },
            "required": ["owner", "repo", "title"],
        },
        "kind": "integration",
        "writes": True,
    },
]


TOOL_EXECUTORS = {
    "github_get_repository": _github_get_repository,
    "github_list_issues": _github_list_issues,
    "github_get_issue": _github_get_issue,
    "github_create_issue": _github_create_issue,
}
