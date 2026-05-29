from __future__ import annotations

from typing import Any

import httpx

from .auth import get_access_token
from .config import get_settings


class GraphAPIError(RuntimeError):
    """Raised when Microsoft Graph returns an error response."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"Microsoft Graph error {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class GraphClient:
    def __init__(
        self,
        access_token: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._access_token = access_token
        self._base_url = base_url
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "GraphClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            settings = get_settings()
            self._client = httpx.AsyncClient(
                base_url=(self._base_url or settings.graph_base_url).rstrip("/"),
                timeout=self._timeout or settings.http_timeout,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._access_token or get_access_token()}",
                },
            )
        return self._client

    async def get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        client = await self._ensure_client()
        response = await client.get(path, params=params)
        return self._parse_response(response)

    async def get_all_pages(
        self,
        path: str,
        params: dict | None = None,
        max_pages: int = 5,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        next_path = path
        next_params = params
        page_count = 0

        while next_path and page_count < max_pages:
            data = await self.get(next_path, params=next_params)
            value = data.get("value", [])
            if not isinstance(value, list):
                raise GraphAPIError(500, "Expected a paged Graph response with a 'value' array.")

            items.extend(item for item in value if isinstance(item, dict))
            next_path = data.get("@odata.nextLink")
            next_params = None
            page_count += 1

        return items

    def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        if response.is_error:
            message = response.text.strip()
            try:
                payload = response.json()
            except ValueError:
                payload = None

            if isinstance(payload, dict):
                graph_error = payload.get("error") or {}
                message = graph_error.get("message") or message or str(payload)

            raise GraphAPIError(response.status_code, message)

        try:
            payload = response.json()
        except ValueError as exc:
            raise GraphAPIError(response.status_code, "Response was not valid JSON.") from exc

        if not isinstance(payload, dict):
            raise GraphAPIError(response.status_code, "Expected a JSON object response from Graph.")

        return payload