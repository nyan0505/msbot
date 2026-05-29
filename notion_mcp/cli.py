"""Notion MCP 최초 인증용 CLI.

사용법::

    python -m notion_mcp.cli auth      # 브라우저로 1회 OAuth 인증
    python -m notion_mcp.cli status    # 저장된 자격증명 상태 확인

`auth` 는 로컬 콜백 서버를 띄우고 브라우저를 열어 인가 코드를 수신한 뒤,
토큰을 디스크에 저장합니다. 이후 봇은 자동 갱신으로 사람 개입 없이 동작합니다.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlparse

from notion_mcp import config, oauth
from notion_mcp.errors import NotionMCPError
from notion_mcp.storage import CredentialStore


class _CallbackHandler(BaseHTTPRequestHandler):
    """OAuth 리디렉션을 1회 수신하는 핸들러."""

    result: dict[str, str] = {}

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler 규약)
        parsed = urlparse(self.path)
        if parsed.path != config.REDIRECT_PATH:
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        _CallbackHandler.result = {k: v[0] for k, v in params.items()}

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if "error" in _CallbackHandler.result:
            msg = "인증에 실패했습니다. 터미널을 확인하세요."
        else:
            msg = "인증이 완료되었습니다. 이 창을 닫아도 됩니다."
        self.wfile.write(
            f"<html><body><h2>{msg}</h2></body></html>".encode("utf-8")
        )

    def log_message(self, *args: object) -> None:  # 콘솔 로그 억제
        pass


def _wait_for_callback(timeout: int = 300) -> dict[str, str]:
    """로컬 서버를 띄우고 콜백을 수신할 때까지 대기합니다."""
    server = HTTPServer((config.REDIRECT_HOST, config.REDIRECT_PORT), _CallbackHandler)
    _CallbackHandler.result = {}

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    deadline = time.time() + timeout
    try:
        while not _CallbackHandler.result and time.time() < deadline:
            time.sleep(0.2)
    finally:
        server.shutdown()
        server.server_close()

    if not _CallbackHandler.result:
        raise NotionMCPError("인증 대기 시간이 초과되었습니다.")
    return _CallbackHandler.result


async def _run_auth() -> None:
    store = CredentialStore()
    redirect_uri = config.REDIRECT_URI

    print("1/5 OAuth 디스커버리 중...")
    metadata = await oauth.discover_oauth_metadata(config.SERVER_URL)
    store.metadata = metadata

    print("2/5 클라이언트 등록 중...")
    # 기존에 등록된 클라이언트가 있으면 재사용.
    client = store.client
    if not (client and client.get("client_id")):
        client = await oauth.register_client(metadata, redirect_uri)
        store.client = client
    store.save()

    print("3/5 PKCE 파라미터 생성...")
    code_verifier, code_challenge = oauth.generate_pkce()
    state = oauth.generate_state()

    auth_url = oauth.build_authorization_url(
        metadata=metadata,
        client_id=client["client_id"],
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        state=state,
    )

    print("4/5 브라우저에서 Notion 인증을 진행하세요.")
    print(f"   브라우저가 열리지 않으면 아래 URL 을 직접 여세요:\n   {auth_url}\n")
    webbrowser.open(auth_url)

    callback = await asyncio.get_event_loop().run_in_executor(None, _wait_for_callback)

    if "error" in callback:
        raise NotionMCPError(
            f"OAuth 오류: {callback.get('error')} - "
            f"{callback.get('error_description', '')}"
        )
    if callback.get("state") != state:
        raise NotionMCPError("state 불일치 - CSRF 가능성으로 중단합니다.")
    code = callback.get("code")
    if not code:
        raise NotionMCPError("콜백에 인가 코드가 없습니다.")

    print("5/5 토큰 교환 중...")
    tokens = await oauth.exchange_code_for_tokens(
        code=code,
        code_verifier=code_verifier,
        metadata=metadata,
        client_id=client["client_id"],
        client_secret=client.get("client_secret"),
        redirect_uri=redirect_uri,
    )
    store.tokens = tokens
    store.save()

    print(f"\n완료! 자격증명을 저장했습니다: {store.path}")
    print("이제 봇이 자동으로 토큰을 갱신하며 동작합니다.")


def _run_status() -> None:
    store = CredentialStore()
    if not store.is_authenticated():
        print("미인증 상태입니다. `python -m notion_mcp.cli auth` 를 실행하세요.")
        sys.exit(1)
    tokens = store.tokens or {}
    expires_at = tokens.get("expires_at", 0)
    remaining = int(expires_at - time.time())
    print(f"인증됨: {store.path}")
    print(f"전송 방식: {store.transport or '(미정 - 첫 호출 시 결정)'}")
    print(f"액세스 토큰 만료까지: {remaining}초")
    print("리프레시 토큰: 있음 (자동 갱신)")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m notion_mcp.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("auth", help="브라우저로 1회 OAuth 인증을 수행합니다.")
    sub.add_parser("status", help="저장된 자격증명 상태를 확인합니다.")
    args = parser.parse_args(argv)

    if args.command == "auth":
        try:
            asyncio.run(_run_auth())
        except NotionMCPError as e:
            print(f"\n인증 실패: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "status":
        _run_status()


if __name__ == "__main__":
    main()
