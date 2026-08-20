"""Feishu integration — Open API client.

Provides the minimal HTTP client used by the Feishu messaging integration:

- obtain tenant_access_token for a custom app
- validate app credentials
- send text messages

Inbound events are handled separately through Feishu's long-connection SDK.
"""

import json
import logging
import threading
import time

import httpx

logger = logging.getLogger(__name__)


FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

_token_lock = threading.Lock()
_cached_token = ""
_token_expires_at = 0.0


def get_tenant_access_token(
    app_id: str,
    app_secret: str,
    *,
    force_refresh: bool = False,
) -> str:
    """Get a tenant_access_token for a Feishu custom app.

    Tokens are cached in memory and refreshed shortly before expiration.

    Raises:
        ValueError: If app credentials are invalid or Feishu rejects the request.
        httpx.HTTPError: If the HTTP request fails.
    """
    global _cached_token, _token_expires_at

    now = time.time()

    if (
        not force_refresh
        and _cached_token
        and now < (_token_expires_at - 300)
    ):
        return _cached_token

    with _token_lock:
        now = time.time()

        if (
            not force_refresh
            and _cached_token
            and now < (_token_expires_at - 300)
        ):
            return _cached_token

        response = httpx.post(
            f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal",
            json={
                "app_id": app_id,
                "app_secret": app_secret,
            },
            timeout=15.0,
        )
        response.raise_for_status()

        data = response.json()

        if data.get("code", 0) != 0:
            raise ValueError(
                f"Feishu token request failed: "
                f"{data.get('msg', 'unknown error')}"
            )

        token = data.get("tenant_access_token", "")
        if not token:
            raise ValueError(
                "Feishu token request succeeded but returned no "
                "tenant_access_token"
            )

        expire = int(data.get("expire", 7200))

        _cached_token = token
        _token_expires_at = time.time() + expire

        return token


def validate_credentials(app_id: str, app_secret: str) -> bool:
    """Validate Feishu app credentials.

    Returns True when a tenant_access_token can be obtained.
    """
    if not app_id or not app_secret:
        return False

    try:
        get_tenant_access_token(
            app_id,
            app_secret,
            force_refresh=True,
        )
        return True
    except Exception as exc:
        logger.warning(
            "Feishu credential validation failed: %s",
            exc,
        )
        return False


def send_text_message(
    receive_id: str,
    text: str,
    app_id: str,
    app_secret: str,
    *,
    receive_id_type: str = "open_id",
) -> dict:
    """Send a text message through the Feishu bot.

    Args:
        receive_id:
            Target user/chat identifier.

        text:
            Message text.

        app_id:
            Feishu custom app ID.

        app_secret:
            Feishu custom app secret.

        receive_id_type:
            Feishu receiver ID type.
            Common values include:
            - open_id
            - user_id
            - union_id
            - email
            - chat_id

    Returns:
        Feishu API response data.

    Raises:
        ValueError:
            If Feishu returns a non-zero business error code.

        httpx.HTTPError:
            If the HTTP request fails.
    """
    token = get_tenant_access_token(app_id, app_secret)

    response = httpx.post(
        f"{FEISHU_API_BASE}/im/v1/messages",
        params={
            "receive_id_type": receive_id_type,
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json={
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps(
                {
                    "text": text,
                },
                ensure_ascii=False,
            ),
        },
        timeout=15.0,
    )
    response.raise_for_status()

    data = response.json()

    if data.get("code", 0) != 0:
        raise ValueError(
            f"Feishu send message failed: "
            f"{data.get('msg', 'unknown error')}"
        )

    return data
