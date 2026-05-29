from __future__ import annotations

import msal
import httpx
import config

_GRAPH_API = "https://graph.microsoft.com/v1.0"
_GRAPH_SCOPES = [
    "https://graph.microsoft.com/Chat.Read",
    "https://graph.microsoft.com/Mail.Read",
]


def get_obo_token(user_assertion: str) -> str:
    """Teams SSO 토큰을 Graph API 토큰으로 교환 (OBO flow)."""
    app = msal.ConfidentialClientApplication(
        client_id=config.APP_ID,
        client_credential=config.APP_SECRET,
        authority=f"https://login.microsoftonline.com/{config.TENANT_ID}",
    )
    result = app.acquire_token_on_behalf_of(
        user_assertion=user_assertion,
        scopes=_GRAPH_SCOPES,
    )
    if "access_token" not in result:
        raise PermissionError(
            f"Graph 토큰 취득 실패: {result.get('error_description', result.get('error'))}"
        )
    return result["access_token"]


async def search_teams_messages(query: str, token: str, top_k: int = 5) -> list[dict]:
    """Graph Search API로 Teams 채팅 메시지를 검색합니다."""
    payload = {
        "requests": [
            {
                "entityTypes": ["chatMessage"],
                "query": {"queryString": query},
                "from": 0,
                "size": top_k,
            }
        ]
    }
    try:
        async with httpx.AsyncClient(timeout=config.SEARCH_TIMEOUT) as client:
            resp = await client.post(
                f"{_GRAPH_API}/search/query",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return _parse_chat_results(resp.json())
    except httpx.TimeoutException:
        raise TimeoutError("Teams 메시지 검색 시간이 초과되었습니다.")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            raise PermissionError("Teams 메시지 검색 권한이 없습니다 (Chat.Read 필요).")
        raise RuntimeError(f"Teams 검색 오류 (HTTP {e.response.status_code}).")


async def search_outlook_messages(query: str, token: str, top_k: int = 5) -> list[dict]:
    """Graph Search API로 Outlook 이메일을 검색합니다."""
    payload = {
        "requests": [
            {
                "entityTypes": ["message"],
                "query": {"queryString": query},
                "from": 0,
                "size": top_k,
            }
        ]
    }
    try:
        async with httpx.AsyncClient(timeout=config.SEARCH_TIMEOUT) as client:
            resp = await client.post(
                f"{_GRAPH_API}/search/query",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return _parse_mail_results(resp.json())
    except httpx.TimeoutException:
        raise TimeoutError("Outlook 메일 검색 시간이 초과되었습니다.")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            raise PermissionError("Outlook 메일 검색 권한이 없습니다 (Mail.Read 필요).")
        raise RuntimeError(f"Outlook 검색 오류 (HTTP {e.response.status_code}).")


async def search_m365(
    query: str,
    user_token: str | None = None,
    top_k: int | None = None,
) -> list[dict]:
    """Teams + Outlook 통합 검색 후 top_k 기준 정렬 반환."""
    if top_k is None:
        top_k = config.SEARCH_TOP_K

    if not user_token:
        return []

    per_source = max(top_k, 3)
    results: list[dict] = []

    for fetch in (
        lambda: search_teams_messages(query, user_token, per_source),
        lambda: search_outlook_messages(query, user_token, per_source),
    ):
        try:
            results.extend(await fetch())
        except (PermissionError, TimeoutError, RuntimeError):
            pass

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results[:top_k]


def format_sources(results: list[dict]) -> str:
    """검색 결과를 LLM context 주입용 문자열로 변환합니다."""
    if not results:
        return ""
    parts = [
        f"[{i}] ({r.get('source_type', '?')}) {r.get('source_label', '')}\n{r.get('body', '')}"
        for i, r in enumerate(results, 1)
    ]
    return "\n\n".join(parts)


def _parse_chat_results(data: dict) -> list[dict]:
    results = []
    for resp in data.get("value", []):
        for hit_container in resp.get("hitsContainers", []):
            for item in hit_container.get("hits", []):
                r = item.get("resource", {})
                sender = r.get("from", {}).get("user", {}).get("displayName", "?")
                results.append({
                    "source_type": "Teams",
                    "source_label": f"Teams 채팅 | {r.get('createdDateTime', '')} | {sender}",
                    "body": r.get("body", {}).get("content", ""),
                    "score": item.get("rank", 0),
                })
    return results


def _parse_mail_results(data: dict) -> list[dict]:
    results = []
    for resp in data.get("value", []):
        for hit_container in resp.get("hitsContainers", []):
            for item in hit_container.get("hits", []):
                r = item.get("resource", {})
                sender = r.get("sender", {}).get("emailAddress", {}).get("name", "?")
                results.append({
                    "source_type": "Outlook",
                    "source_label": (
                        f"메일 | {r.get('subject', '제목 없음')}"
                        f" | {sender}"
                        f" | {r.get('receivedDateTime', '')}"
                    ),
                    "body": r.get("bodyPreview", ""),
                    "score": item.get("rank", 0),
                })
    return results
