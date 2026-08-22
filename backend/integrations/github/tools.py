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

async def _github_list_pull_requests(
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
            f"/repos/{owner}/{repo}/pulls",
            params={
                "state": state,
                "per_page": limit,
            },
        )

        pulls = [
            {
                "number": item.get("number"),
                "title": item.get("title"),
                "state": item.get("state"),
                "draft": item.get("draft"),
                "user": (item.get("user") or {}).get("login"),
                "head": (item.get("head") or {}).get("ref"),
                "base": (item.get("base") or {}).get("ref"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "html_url": item.get("html_url"),
            }
            for item in data
        ]

        return {
            "pull_requests": pulls,
            "count": len(pulls),
        }

    except httpx.HTTPStatusError as e:
        logger.error("github_list_pull_requests error: %s", e)
        return {"error": f"GitHub API returned {e.response.status_code}"}

    except Exception as e:
        logger.error("github_list_pull_requests error: %s", e)
        return {"error": str(e)}


async def _github_get_pull_request(
    owner: str,
    repo: str,
    pull_number: int,
) -> dict:
    client = get_client()

    if not client:
        return {"error": "GitHub not configured"}

    try:
        data = await client.get(
            f"/repos/{owner}/{repo}/pulls/{pull_number}"
        )

        return {
            "pull_request": {
                "number": data.get("number"),
                "title": data.get("title"),
                "body": data.get("body"),
                "state": data.get("state"),
                "draft": data.get("draft"),
                "merged": data.get("merged"),
                "mergeable": data.get("mergeable"),
                "user": (data.get("user") or {}).get("login"),
                "head": (data.get("head") or {}).get("ref"),
                "base": (data.get("base") or {}).get("ref"),
                "commits": data.get("commits"),
                "changed_files": data.get("changed_files"),
                "additions": data.get("additions"),
                "deletions": data.get("deletions"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "html_url": data.get("html_url"),
            }
        }

    except httpx.HTTPStatusError as e:
        logger.error("github_get_pull_request error: %s", e)
        return {"error": f"GitHub API returned {e.response.status_code}"}

    except Exception as e:
        logger.error("github_get_pull_request error: %s", e)
        return {"error": str(e)}

async def _github_get_pull_request_diff(
    owner: str,
    repo: str,
    pull_number: int,
) -> dict:
    client = get_client()

    if not client:
        return {"error": "GitHub not configured"}

    try:
        diff = await client.get_text(
            f"/repos/{owner}/{repo}/pulls/{pull_number}",
            accept="application/vnd.github.v3.diff",
        )

        return {
            "pull_number": pull_number,
            "diff": diff,
            "has_changes": bool(diff.strip()),
        }

    except httpx.HTTPStatusError as e:
        logger.error("github_get_pull_request_diff error: %s", e)
        return {"error": f"GitHub API returned {e.response.status_code}"}

    except Exception as e:
        logger.error("github_get_pull_request_diff error: %s", e)
        return {"error": str(e)}

async def _github_get_issue_comments(
    owner: str,
    repo: str,
    issue_number: int,
    limit: int = 50,
) -> dict:
    client = get_client()

    if not client:
        return {"error": "GitHub not configured"}

    limit = max(1, min(limit, 100))

    try:
        data = await client.get(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            params={"per_page": limit},
        )

        comments = [
            {
                "id": item.get("id"),
                "user": (item.get("user") or {}).get("login"),
                "body": item.get("body"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "html_url": item.get("html_url"),
            }
            for item in data
        ]

        return {
            "comments": comments,
            "count": len(comments),
        }

    except httpx.HTTPStatusError as e:
        logger.error("github_get_issue_comments error: %s", e)
        return {"error": f"GitHub API returned {e.response.status_code}"}

    except Exception as e:
        logger.error("github_get_issue_comments error: %s", e)
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
    {
        "name": "github_list_pull_requests",
        "description": (
            "List pull requests in a GitHub repository. "
            "Use this to inspect active or historical code review work."
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
                    "description": "Pull request state. Defaults to open.",
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Maximum pull requests to return. "
                        "Defaults to 20, max 100."
                    ),
                },
            },
            "required": ["owner", "repo"],
        },
        "kind": "integration",
    },

    {
        "name": "github_get_pull_request",
        "description": (
            "Read a single GitHub pull request including title, body, state, "
            "author, source branch, target branch, merge status, commit count, "
            "changed file count, additions, and deletions."
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
                "pull_number": {
                    "type": "integer",
                    "description": "GitHub pull request number.",
                },
            },
            "required": ["owner", "repo", "pull_number"],
        },
        "kind": "integration",
    },

    {
        "name": "github_get_pull_request_diff",
        "description": (
            "Get the unified diff for a GitHub pull request. "
            "Use this to inspect the exact code changes proposed by the pull request."
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
                "pull_number": {
                    "type": "integer",
                    "description": "GitHub pull request number.",
                },
            },
            "required": ["owner", "repo", "pull_number"],
        },
        "kind": "integration",
    },

    {
        "name": "github_get_issue_comments",
        "description": (
            "List conversation comments on a GitHub issue or pull request. "
            "GitHub pull requests share the issue comments API for general discussion comments."
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
                    "description": (
                        "Issue or pull request number whose conversation comments "
                        "should be listed."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Maximum comments to return. Defaults to 50, max 100."
                    ),
                },
            },
            "required": ["owner", "repo", "issue_number"],
        },
        "kind": "integration",
    },
]


TOOL_EXECUTORS = {
    "github_get_repository": _github_get_repository,
    "github_list_issues": _github_list_issues,
    "github_get_issue": _github_get_issue,
    "github_create_issue": _github_create_issue,
    "github_list_pull_requests": _github_list_pull_requests,
    "github_get_pull_request": _github_get_pull_request,
    "github_get_pull_request_diff": _github_get_pull_request_diff,
    "github_get_issue_comments": _github_get_issue_comments,
}
