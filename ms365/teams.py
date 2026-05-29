from __future__ import annotations

from ._utils import build_date_range, contains_query, is_within_range, make_snippet, strip_html
from .graph_client import GraphClient
from .schemas import TeamsSearchResult


async def search_my_teams_chats(
    query: str,
    start_date: str,
    end_date: str,
    limit_per_chat: int = 50,
    max_chats: int = 20,
) -> list[TeamsSearchResult]:
    start_dt, end_dt = build_date_range(start_date, end_date)
    chat_page_size = min(max(max_chats, 1), 50)
    message_page_size = min(max(limit_per_chat, 1), 50)

    async with GraphClient() as client:
        chats = await client.get_all_pages(
            "/me/chats",
            params={"$select": "id,topic,webUrl", "$top": str(chat_page_size)},
            max_pages=2,
        )
        chats = chats[:max_chats]

        participant_cache: dict[str, list[str]] = {}
        results: list[TeamsSearchResult] = []

        for chat in chats:
            chat_id = chat.get("id")
            if not chat_id:
                continue

            messages = await client.get_all_pages(
                f"/chats/{chat_id}/messages",
                params={
                    "$select": "id,createdDateTime,from,body,webUrl",
                    "$top": str(message_page_size),
                },
                max_pages=1,
            )

            matched_messages: list[tuple[dict, str]] = []
            for message in messages:
                if not is_within_range(message.get("createdDateTime"), start_dt, end_dt):
                    continue

                body = strip_html((message.get("body") or {}).get("content"))
                if not contains_query(query, body):
                    continue

                matched_messages.append((message, body))

            if not matched_messages:
                continue

            participants = participant_cache.get(chat_id)
            if participants is None:
                participants = await _get_chat_participants(client, chat_id)
                participant_cache[chat_id] = participants

            for message, body in matched_messages:
                results.append(
                    TeamsSearchResult(
                        chat_id=chat_id,
                        message_id=message["id"],
                        created_at=message.get("createdDateTime"),
                        sender=_get_sender_name(message.get("from")),
                        participants=participants,
                        snippet=make_snippet(body, query),
                        web_url=message.get("webUrl") or chat.get("webUrl"),
                    )
                )

    results.sort(key=lambda item: item.created_at or "", reverse=True)
    return results


async def _get_chat_participants(client: GraphClient, chat_id: str) -> list[str]:
    members = await client.get_all_pages(
        f"/chats/{chat_id}/members",
        params={"$top": "50"},
        max_pages=2,
    )

    participants: list[str] = []
    for member in members:
        name = member.get("displayName") or member.get("email") or member.get("userId")
        if name and name not in participants:
            participants.append(name)
    return participants


def _get_sender_name(sender: dict | None) -> str | None:
    if not isinstance(sender, dict):
        return None

    for sender_type in ("user", "application", "device"):
        payload = sender.get(sender_type)
        if isinstance(payload, dict):
            display_name = payload.get("displayName")
            if display_name:
                return display_name

    return None