"""Notion MCP 클라이언트 (Step 7: MCP 서버 연결 + 공개 인터페이스).

봇 협업자가 import 해서 사용하는 진입점입니다::

    from notion_mcp.client import NotionMCP

    notion = NotionMCP()
    results = await notion.search("질의")
    content = await notion.read_page("page_id")
    context = await notion.search_and_read("질의")

저장된 토큰을 자동으로 로드/갱신하므로 사람 개입 없이 24/7 동작합니다.
최초 1회 `python -m notion_mcp.cli auth` 로 인증이 필요합니다.
"""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

from notion_mcp import config, oauth
from notion_mcp.errors import NotAuthenticatedError, NotionMCPError
from notion_mcp.storage import CredentialStore

# Notion MCP 도구 이름 후보. 서버가 노출하는 도구 이름이 바뀌어도 동작하도록
# list_tools 결과에서 패턴 매칭으로 해석합니다.
_SEARCH_TOOL_CANDIDATES = ("search", "notion-search", "notion_search")
_FETCH_TOOL_CANDIDATES = ("fetch", "notion-fetch", "retrieve-page", "notion_fetch")


class NotionMCP:
    """Notion 호스티드 MCP 서버에 대한 비동기 클라이언트."""

    def __init__(self, store: CredentialStore | None = None) -> None:
        self._store = store or CredentialStore()
        self._refresh_lock = asyncio.Lock()
        self._tool_names: list[str] | None = None

    # --- 인증/토큰 ------------------------------------------------------

    async def ensure_valid_token(self) -> str:
        """유효한 액세스 토큰을 반환합니다. 만료 임박 시 선제적으로 갱신합니다."""
        async with self._refresh_lock:
            self._store.load()  # 다른 프로세스가 회전시킨 토큰 반영
            tokens = self._store.tokens
            if not tokens or not tokens.get("refresh_token"):
                raise NotAuthenticatedError(
                    "저장된 Notion 자격증명이 없습니다. "
                    "먼저 `python -m notion_mcp.cli auth` 를 실행하세요."
                )

            expires_at = tokens.get("expires_at", 0)
            if time.time() < expires_at - config.TOKEN_REFRESH_LEEWAY:
                return tokens["access_token"]

            return await self._refresh_locked()

    async def _refresh_locked(self) -> str:
        """리프레시 토큰으로 액세스 토큰을 갱신합니다 (락 보유 상태 가정)."""
        metadata = self._store.metadata
        client = self._store.client
        tokens = self._store.tokens
        if not (metadata and client and tokens):
            raise NotAuthenticatedError("자격증명이 불완전합니다. 재인증이 필요합니다.")

        new_tokens = await oauth.refresh_access_token(
            refresh_token=tokens["refresh_token"],
            metadata=metadata,
            client_id=client["client_id"],
            client_secret=client.get("client_secret"),
        )
        self._store.tokens = new_tokens
        self._store.save()
        return new_tokens["access_token"]

    def _auth_headers(self, access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": config.USER_AGENT,
        }

    # --- Step 7: MCP 서버 연결 -----------------------------------------

    async def _detect_transport(self, access_token: str) -> str:
        """사용할 전송 방식을 결정합니다. Streamable HTTP 우선, 실패 시 SSE."""
        cached = self._store.transport
        if cached in ("streamable", "sse"):
            return cached

        headers = self._auth_headers(access_token)
        try:
            async with streamablehttp_client(config.SERVER_URL, headers=headers) as (
                read,
                write,
                _,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
            transport = "streamable"
        except Exception:
            transport = "sse"

        self._store.transport = transport
        self._store.save()
        return transport

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[ClientSession]:
        """인증된 MCP 세션을 여는 컨텍스트 매니저."""
        access_token = await self.ensure_valid_token()
        transport = await self._detect_transport(access_token)
        headers = self._auth_headers(access_token)

        if transport == "streamable":
            async with streamablehttp_client(config.SERVER_URL, headers=headers) as (
                read,
                write,
                _,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session
        else:
            async with sse_client(config.SSE_URL, headers=headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

    async def _resolve_tool(
        self, session: ClientSession, candidates: tuple[str, ...]
    ) -> str:
        """list_tools 결과에서 후보 이름과 매칭되는 실제 도구 이름을 찾습니다."""
        if self._tool_names is None:
            result = await session.list_tools()
            self._tool_names = [t.name for t in result.tools]

        names = self._tool_names
        # 1) 정확히 일치
        for cand in candidates:
            if cand in names:
                return cand
        # 2) 부분 일치 (예: "notion-search" 의 "search")
        for cand in candidates:
            for name in names:
                if cand in name:
                    return name
        raise NotionMCPError(
            f"필요한 도구를 찾지 못했습니다. 후보={candidates}, 사용 가능={names}"
        )

    # --- 공개 인터페이스 ------------------------------------------------

    async def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """워크스페이스를 검색하고 결과 목록을 반환합니다.

        Args:
            query: 검색어.
            **kwargs: Notion search 도구에 전달할 추가 인자.

        Returns:
            결과 dict 리스트. 가능하면 구조화된 결과를, 아니면
            ``[{"text": "<원문>"}]`` 형태를 반환합니다.
        """
        async with self._session() as session:
            tool = await self._resolve_tool(session, _SEARCH_TOOL_CANDIDATES)
            args = {"query": query}
            args.update(kwargs)
            result = await session.call_tool(tool, args)
            return _extract_results(result)

    async def read_page(self, page_id: str, **kwargs: Any) -> str:
        """페이지/URL 의 내용을 텍스트로 읽어옵니다.

        Args:
            page_id: Notion 페이지 ID 또는 URL.
            **kwargs: fetch 도구에 전달할 추가 인자.
        """
        async with self._session() as session:
            tool = await self._resolve_tool(session, _FETCH_TOOL_CANDIDATES)
            args = {"id": page_id}
            args.update(kwargs)
            result = await session.call_tool(tool, args)
            return _extract_text(result)

    async def search_and_read(
        self, query: str, top_k: int | None = None
    ) -> str:
        """검색 후 상위 결과의 본문을 읽어 LLM 컨텍스트용 문자열로 합칩니다.

        Args:
            query: 검색어.
            top_k: 본문을 읽어올 상위 결과 개수 (기본 config 값).
        """
        if top_k is None:
            top_k = config.SEARCH_AND_READ_TOP_K

        results = await self.search(query)
        if not results:
            return ""

        ids = _extract_page_ids(results)[:top_k]
        if not ids:
            # 페이지 ID 를 추출하지 못하면 검색 원문이라도 반환.
            return "\n\n".join(
                r.get("text", "") for r in results if r.get("text")
            ).strip()

        sections: list[str] = []
        for page_id in ids:
            try:
                content = await self.read_page(page_id)
            except NotionMCPError:
                continue
            if content:
                sections.append(f"[Notion: {page_id}]\n{content}")
        return "\n\n".join(sections).strip()


# --- 응답 파싱 헬퍼 ---------------------------------------------------------


def _content_text(result: Any) -> str:
    """CallToolResult 의 content 블록에서 텍스트를 연결합니다."""
    parts: list[str] = []
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _extract_text(result: Any) -> str:
    """도구 호출 결과를 사람이 읽을 수 있는 텍스트로 변환합니다."""
    structured = getattr(result, "structuredContent", None)
    if structured:
        return json.dumps(structured, ensure_ascii=False, indent=2)
    return _content_text(result)


def _extract_results(result: Any) -> list[dict[str, Any]]:
    """검색 결과를 dict 리스트로 best-effort 파싱합니다."""
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        for key in ("results", "items", "pages", "value"):
            if isinstance(structured.get(key), list):
                return structured[key]
        return [structured]
    if isinstance(structured, list):
        return structured

    text = _content_text(result)
    if not text:
        return []
    # 텍스트가 JSON 이면 파싱 시도.
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return [{"text": text}]
    if isinstance(parsed, list):
        return [p if isinstance(p, dict) else {"text": str(p)} for p in parsed]
    if isinstance(parsed, dict):
        for key in ("results", "items", "pages", "value"):
            if isinstance(parsed.get(key), list):
                return parsed[key]
        return [parsed]
    return [{"text": text}]


def _extract_page_ids(results: list[dict[str, Any]]) -> list[str]:
    """검색 결과 dict 에서 페이지 ID/URL 을 추출합니다."""
    ids: list[str] = []
    for r in results:
        if not isinstance(r, dict):
            continue
        for key in ("id", "page_id", "pageId", "url", "uri"):
            value = r.get(key)
            if isinstance(value, str) and value:
                ids.append(value)
                break
    return ids
