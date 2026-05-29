from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from notion_mcp import config


class CredentialStore:
    """OAuth 메타데이터/클라이언트 자격증명/토큰을 JSON 파일로 영속화합니다.

    파일 구조::

        {
          "metadata":  { ... OAuth 서버 메타데이터 ... },
          "client":    { "client_id": ..., "client_secret": ... },
          "tokens":    { "access_token": ..., "refresh_token": ...,
                          "expires_at": <epoch>, "token_type": "Bearer" },
          "transport": "streamable" | "sse"
        }

    파일은 소유자 전용 권한(0600)으로 저장됩니다.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path: Path = Path(path) if path else config.TOKEN_PATH
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # 원자적 쓰기: 임시 파일에 기록 후 교체.
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    # --- 접근자 --------------------------------------------------------

    @property
    def metadata(self) -> dict[str, Any] | None:
        return self._data.get("metadata")

    @metadata.setter
    def metadata(self, value: dict[str, Any]) -> None:
        self._data["metadata"] = value

    @property
    def client(self) -> dict[str, Any] | None:
        return self._data.get("client")

    @client.setter
    def client(self, value: dict[str, Any]) -> None:
        self._data["client"] = value

    @property
    def tokens(self) -> dict[str, Any] | None:
        return self._data.get("tokens")

    @tokens.setter
    def tokens(self, value: dict[str, Any]) -> None:
        self._data["tokens"] = value

    @property
    def transport(self) -> str | None:
        return self._data.get("transport")

    @transport.setter
    def transport(self, value: str) -> None:
        self._data["transport"] = value

    def is_authenticated(self) -> bool:
        tokens = self.tokens
        return bool(tokens and tokens.get("refresh_token"))
