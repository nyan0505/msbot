"""Notion MCP OAuth 2.0 + PKCE 구현.

Notion 공식 가이드("Integrating your own MCP client")의 8단계를 따릅니다:
  1. OAuth 디스커버리 (RFC 9470 → RFC 8414)
  2. PKCE 파라미터 생성 (RFC 7636)
  3. 동적 클라이언트 등록 (RFC 7591)
  4. 인가 요청 URL 생성
  5. 콜백 처리 (state 검증)
  6. 인가 코드 → 토큰 교환
  8. 토큰 갱신 (리프레시 토큰 회전 처리)
"""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode, urljoin

import httpx
from authlib.common.security import generate_token
from authlib.oauth2.rfc7636 import create_s256_code_challenge

from notion_mcp import config
from notion_mcp.errors import NotionMCPError, ReauthRequiredError


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=config.HTTP_TIMEOUT,
        headers={"User-Agent": config.USER_AGENT},
    )


# --- Step 1: OAuth 디스커버리 ------------------------------------------------


async def discover_oauth_metadata(server_url: str) -> dict[str, Any]:
    """RFC 9470 + RFC 8414 디스커버리로 OAuth 엔드포인트를 찾습니다.

    1. Protected Resource Metadata 에서 인가 서버 목록을 얻고
    2. Authorization Server Metadata 에서 실제 OAuth 엔드포인트를 얻습니다.
    """
    protected_resource_url = urljoin(server_url, "/.well-known/oauth-protected-resource")

    async with _client() as client:
        resp = await client.get(protected_resource_url)
        if resp.status_code != 200:
            raise NotionMCPError(
                f"Protected Resource Metadata 조회 실패: {resp.status_code}"
            )
        protected_resource = resp.json()
        auth_servers = protected_resource.get("authorization_servers")
        if not isinstance(auth_servers, list) or not auth_servers:
            raise NotionMCPError("Protected Resource Metadata 에 인가 서버가 없습니다.")

        auth_server_url = auth_servers[0]
        metadata_url = urljoin(auth_server_url, "/.well-known/oauth-authorization-server")
        meta_resp = await client.get(metadata_url)
        if meta_resp.status_code != 200:
            raise NotionMCPError(
                f"Authorization Server Metadata 조회 실패: {meta_resp.status_code}"
            )
        metadata: dict[str, Any] = meta_resp.json()

    if not metadata.get("authorization_endpoint") or not metadata.get("token_endpoint"):
        raise NotionMCPError("OAuth 메타데이터에 필수 엔드포인트가 없습니다.")

    return metadata


# --- Step 2: PKCE 파라미터 생성 ---------------------------------------------


def generate_pkce() -> tuple[str, str]:
    """PKCE code_verifier 와 S256 code_challenge 를 생성합니다.

    Returns:
        (code_verifier, code_challenge)
    """
    code_verifier = generate_token(48)
    code_challenge = create_s256_code_challenge(code_verifier)
    return code_verifier, code_challenge


def generate_state() -> str:
    """CSRF 방지용 state 값을 생성합니다."""
    return generate_token(32)


# --- Step 3: 동적 클라이언트 등록 -------------------------------------------


async def register_client(metadata: dict[str, Any], redirect_uri: str) -> dict[str, Any]:
    """RFC 7591 동적 클라이언트 등록을 수행합니다."""
    registration_endpoint = metadata.get("registration_endpoint")
    if not registration_endpoint:
        raise NotionMCPError("서버가 동적 클라이언트 등록을 지원하지 않습니다.")

    registration_request = {
        "client_name": config.CLIENT_NAME,
        "client_uri": config.CLIENT_URI,
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    if config.SCOPES:
        registration_request["scope"] = " ".join(config.SCOPES)

    async with _client() as client:
        resp = await client.post(
            registration_endpoint,
            json=registration_request,
            headers={"Accept": "application/json"},
        )
        if resp.status_code not in (200, 201):
            raise NotionMCPError(
                f"클라이언트 등록 실패: {resp.status_code} - {resp.text}"
            )
        credentials: dict[str, Any] = resp.json()

    if not credentials.get("client_id"):
        raise NotionMCPError("클라이언트 등록 응답에 client_id 가 없습니다.")
    return credentials


# --- Step 4: 인가 요청 URL 생성 ---------------------------------------------


def build_authorization_url(
    metadata: dict[str, Any],
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    state: str,
) -> str:
    """PKCE 파라미터를 포함한 인가 요청 URL 을 생성합니다."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(config.SCOPES),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "consent",
    }
    return f"{metadata['authorization_endpoint']}?{urlencode(params)}"


# --- Step 6: 인가 코드 → 토큰 교환 ------------------------------------------


async def exchange_code_for_tokens(
    code: str,
    code_verifier: str,
    metadata: dict[str, Any],
    client_id: str,
    client_secret: str | None,
    redirect_uri: str,
) -> dict[str, Any]:
    """인가 코드를 액세스/리프레시 토큰으로 교환합니다."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    if client_secret:
        data["client_secret"] = client_secret

    async with _client() as client:
        resp = await client.post(
            metadata["token_endpoint"],
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        if resp.status_code != 200:
            raise NotionMCPError(f"토큰 교환 실패: {resp.status_code} - {resp.text}")
        tokens: dict[str, Any] = resp.json()

    if not tokens.get("access_token"):
        raise NotionMCPError("토큰 응답에 access_token 이 없습니다.")
    return _normalize_tokens(tokens)


# --- Step 8: 토큰 갱신 ------------------------------------------------------


async def refresh_access_token(
    refresh_token: str,
    metadata: dict[str, Any],
    client_id: str,
    client_secret: str | None,
) -> dict[str, Any]:
    """리프레시 토큰으로 새 액세스 토큰을 발급받습니다.

    Notion 은 리프레시 토큰을 회전시키므로, 응답에 새 refresh_token 이 있으면
    반드시 저장해야 합니다(`_normalize_tokens` 에서 보존). invalid_grant 응답은
    재인증 필요(`ReauthRequiredError`)로 변환합니다.
    """
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }
    if client_secret:
        data["client_secret"] = client_secret

    async with _client() as client:
        resp = await client.post(
            metadata["token_endpoint"],
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        if resp.status_code != 200:
            error_code = None
            try:
                error_code = resp.json().get("error")
            except Exception:
                pass
            if error_code == "invalid_grant":
                raise ReauthRequiredError(
                    "리프레시 토큰이 무효화되었습니다. 재인증이 필요합니다 "
                    "(python -m notion_mcp.cli auth)."
                )
            raise NotionMCPError(
                f"토큰 갱신 실패: {resp.status_code} - {resp.text}"
            )
        tokens: dict[str, Any] = resp.json()

    # 회전된 refresh_token 이 없으면 기존 것을 유지.
    tokens.setdefault("refresh_token", refresh_token)
    return _normalize_tokens(tokens)


def _normalize_tokens(tokens: dict[str, Any]) -> dict[str, Any]:
    """토큰 응답에 절대 만료시각(expires_at)을 추가합니다."""
    expires_in = int(tokens.get("expires_in", 3600))
    tokens = dict(tokens)
    tokens["expires_at"] = int(time.time()) + expires_in
    return tokens
