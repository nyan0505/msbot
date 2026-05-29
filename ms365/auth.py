from __future__ import annotations

from pathlib import Path

import msal

from .config import get_settings

_MSAL_RESERVED_SCOPES = {"openid", "profile", "offline_access"}


class AuthenticationError(RuntimeError):
    """Raised when delegated Microsoft authentication fails."""


def _load_token_cache(cache_path: Path) -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if cache_path.exists():
        cache.deserialize(cache_path.read_text())
    return cache


def _save_token_cache(cache: msal.SerializableTokenCache, cache_path: Path) -> None:
    if not cache.has_state_changed:
        return
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(cache.serialize())


def get_access_token() -> str:
    settings = get_settings()
    msal_scopes = [scope for scope in settings.scopes if scope not in _MSAL_RESERVED_SCOPES]
    cache = _load_token_cache(settings.token_cache_path)
    app = msal.PublicClientApplication(
        client_id=settings.client_id,
        authority=f"https://login.microsoftonline.com/{settings.tenant_id}",
        token_cache=cache,
    )

    result: dict | None = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(msal_scopes, account=accounts[0])

    if not result:
        flow = app.initiate_device_flow(scopes=msal_scopes)
        if "user_code" not in flow:
            raise AuthenticationError(f"Failed to start device-code flow: {flow}")

        print(flow.get("message", "Open the provided URL and complete Microsoft sign-in."))
        result = app.acquire_token_by_device_flow(flow)

    _save_token_cache(cache, settings.token_cache_path)

    if not result or "access_token" not in result:
        description = (result or {}).get("error_description") or (result or {}).get("error")
        raise AuthenticationError(f"Failed to get Microsoft Graph access token: {description}")

    return result["access_token"]