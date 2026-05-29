from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Notion 호스티드 MCP 엔드포인트 (가이드 Overview 참고).
# Streamable HTTP 를 우선 시도하고 실패 시 SSE 로 폴백합니다.
SERVER_URL: str = os.environ.get("NOTION_MCP_SERVER_URL", "https://mcp.notion.com/mcp")
SSE_URL: str = os.environ.get("NOTION_MCP_SSE_URL", "https://mcp.notion.com/sse")

# 동적 클라이언트 등록(RFC 7591)에 사용할 클라이언트 메타데이터.
CLIENT_NAME: str = os.environ.get("NOTION_MCP_CLIENT_NAME", "HD Hyundai ERC Assistant")
CLIENT_URI: str = os.environ.get("NOTION_MCP_CLIENT_URI", "https://github.com/hd-hyundai-erc")

# 로컬 OAuth 콜백 서버. 최초 인증(`cli auth`) 시에만 사용됩니다.
REDIRECT_HOST: str = os.environ.get("NOTION_MCP_REDIRECT_HOST", "localhost")
REDIRECT_PORT: int = int(os.environ.get("NOTION_MCP_REDIRECT_PORT", "8765"))
REDIRECT_PATH: str = os.environ.get("NOTION_MCP_REDIRECT_PATH", "/callback")
REDIRECT_URI: str = os.environ.get(
    "NOTION_MCP_REDIRECT_URI",
    f"http://{REDIRECT_HOST}:{REDIRECT_PORT}{REDIRECT_PATH}",
)

# 요청 스코프. Notion 은 빈 스코프로 워크스페이스 동의를 처리합니다.
SCOPES: list[str] = [s for s in os.environ.get("NOTION_MCP_SCOPES", "").split() if s]

USER_AGENT: str = os.environ.get("NOTION_MCP_USER_AGENT", "HDHyundaiERC-NotionMCP/1.0")

# 토큰/클라이언트 자격증명 영속화 경로. 봇이 24/7 동작하도록 디스크에 저장합니다.
TOKEN_PATH: Path = Path(
    os.environ.get(
        "NOTION_MCP_TOKEN_PATH",
        str(Path.home() / ".notion_mcp" / "credentials.json"),
    )
).expanduser()

# 액세스 토큰 만료 N초 전부터 선제적으로 갱신합니다. Notion 토큰은 1시간 만료.
TOKEN_REFRESH_LEEWAY: int = int(os.environ.get("NOTION_MCP_REFRESH_LEEWAY", "120"))

# 네트워크 타임아웃(초).
HTTP_TIMEOUT: int = int(os.environ.get("NOTION_MCP_HTTP_TIMEOUT", "30"))
MCP_TIMEOUT: int = int(os.environ.get("NOTION_MCP_TIMEOUT", "60"))

# search_and_read 시 본문을 읽어올 상위 결과 개수.
SEARCH_AND_READ_TOP_K: int = int(os.environ.get("NOTION_MCP_SEARCH_READ_TOP_K", "3"))
