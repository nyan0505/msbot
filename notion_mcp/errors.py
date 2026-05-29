from __future__ import annotations


class NotionMCPError(RuntimeError):
    """Notion MCP 클라이언트 관련 기본 예외."""


class NotAuthenticatedError(NotionMCPError):
    """저장된 토큰이 없어 인증이 필요한 경우.

    `python -m notion_mcp.cli auth` 로 최초 인증을 수행해야 합니다.
    """


class ReauthRequiredError(NotionMCPError):
    """리프레시 토큰이 만료/무효화되어 재인증이 필요한 경우.

    OAuth 서버가 `invalid_grant` 을 반환하면 발생합니다. 사용자가 다시
    `python -m notion_mcp.cli auth` 를 실행해야 합니다.
    """
