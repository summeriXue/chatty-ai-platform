import logging

import httpx

from integrations.registry import save_credentials


logger = logging.getLogger(__name__)


GITHUB_API_BASE = "https://api.github.com"


def test_connection(api_token: str) -> dict:
    """Validate a GitHub personal access token."""

    try:
        response = httpx.get(
            f"{GITHUB_API_BASE}/user",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15.0,
        )

        if response.status_code != 200:
            return {
                "ok": False,
                "error": f"GitHub returned HTTP {response.status_code}",
            }

        data = response.json()

        return {
            "ok": True,
            "login": data.get("login", ""),
        }

    except Exception as e:
        logger.error("GitHub connection test failed: %s", e)
        return {
            "ok": False,
            "error": str(e),
        }


def setup(api_token: str) -> dict:
    """Validate GitHub API token and save credentials."""

    api_token = api_token.strip()

    if not api_token:
        return {
            "ok": False,
            "error": "GitHub token is required",
        }

    result = test_connection(api_token)

    if not result["ok"]:
        return result

    save_credentials(
        "github",
        {
            "api_key": api_token,
            "enabled": True,
        },
    )

    return {
        "ok": True,
        "login": result.get("login", ""),
    }
