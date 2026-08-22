import httpx


GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str):
        self.token = token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get(self, path: str, params: dict | None = None) -> dict | list:
        async with httpx.AsyncClient(
            base_url=GITHUB_API_BASE,
            headers=self._headers(),
            timeout=20.0,
        ) as client:
            response = await client.get(path, params=params)

        response.raise_for_status()
        return response.json()

    async def post(
        self,
        path: str,
        json: dict | None = None,
    ) -> dict:
        async with httpx.AsyncClient(
            base_url=GITHUB_API_BASE,
            headers=self._headers(),
            timeout=20.0,
        ) as client:
            response = await client.post(
                path,
                json=json,
            )

        response.raise_for_status()
        return response.json()


def get_client() -> GitHubClient | None:
    from integrations.registry import get_credentials, is_enabled

    if not is_enabled("github"):
        return None

    creds = get_credentials("github")
    token = creds.get("api_key", "")

    if not token:
        return None

    return GitHubClient(token)
