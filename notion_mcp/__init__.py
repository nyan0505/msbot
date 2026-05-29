"""Notion 원격 MCP 클라이언트 패키지.

사내 Teams 봇에서 Notion 호스티드 MCP 서버(mcp.notion.com)에 연결하기 위한
모듈입니다. OAuth 2.0 + PKCE 인증, 토큰 영속화/자동 갱신, Streamable HTTP
연결(SSE 폴백)을 처리합니다.

사용 예시::

    from notion_mcp.client import NotionMCP

    notion = NotionMCP()
    results = await notion.search("질의")
    content = await notion.read_page("page_id")
    context = await notion.search_and_read("질의")

최초 1회 인증::

    python -m notion_mcp.cli auth
"""

from notion_mcp.client import NotionMCP
from notion_mcp.errors import (
    NotAuthenticatedError,
    NotionMCPError,
    ReauthRequiredError,
)

__all__ = [
    "NotionMCP",
    "NotionMCPError",
    "NotAuthenticatedError",
    "ReauthRequiredError",
]
