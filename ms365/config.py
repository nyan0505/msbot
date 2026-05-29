from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
DEFAULT_GRAPH_SCOPES = [
    "User.Read",
    "Mail.Read",
    "Chat.Read",
    "Calendars.Read",
    "offline_access",
]


@dataclass(frozen=True)
class MS365Settings:
    tenant_id: str
    client_id: str
    scopes: list[str]
    graph_base_url: str
    token_cache_path: Path
    http_timeout: float


def _parse_scopes(raw_value: str | None) -> list[str]:
    scopes = [item.strip() for item in (raw_value or "").split() if item.strip()]
    return scopes or DEFAULT_GRAPH_SCOPES.copy()


@lru_cache(maxsize=1)
def get_settings() -> MS365Settings:
    tenant_id = os.environ.get("MS_TENANT_ID", "").strip()
    client_id = os.environ.get("MS_CLIENT_ID", "").strip()

    if not tenant_id:
        raise RuntimeError("MS_TENANT_ID is required for Microsoft Graph delegated auth.")
    if not client_id:
        raise RuntimeError("MS_CLIENT_ID is required for Microsoft Graph delegated auth.")

    token_cache_path = Path(
        os.environ.get(
            "MS_GRAPH_TOKEN_CACHE_PATH",
            str(Path.home() / ".ms365" / "token_cache.json"),
        )
    ).expanduser()

    return MS365Settings(
        tenant_id=tenant_id,
        client_id=client_id,
        scopes=_parse_scopes(os.environ.get("MS_GRAPH_SCOPES")),
        graph_base_url=os.environ.get("MS_GRAPH_BASE_URL", DEFAULT_GRAPH_BASE_URL).rstrip("/"),
        token_cache_path=token_cache_path,
        http_timeout=float(os.environ.get("MS_GRAPH_TIMEOUT", "30")),
    )