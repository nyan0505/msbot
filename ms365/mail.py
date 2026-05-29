from __future__ import annotations

from ._utils import build_date_range, contains_query, email_address_name, graph_datetime
from .graph_client import GraphClient
from .schemas import MailSearchResult


async def search_my_outlook_mail(
    query: str,
    start_date: str,
    end_date: str,
    limit: int = 20,
) -> list[MailSearchResult]:
    start_dt, end_dt = build_date_range(start_date, end_date)
    fetch_size = min(max(limit * 3, limit), 100)

    params = {
        "$select": "id,subject,from,receivedDateTime,bodyPreview,webLink",
        "$filter": (
            f"receivedDateTime ge {graph_datetime(start_dt)} "
            f"and receivedDateTime le {graph_datetime(end_dt)}"
        ),
        "$orderby": "receivedDateTime desc",
        "$top": str(fetch_size),
    }

    async with GraphClient() as client:
        messages = await client.get_all_pages("/me/messages", params=params, max_pages=3)

    results: list[MailSearchResult] = []
    for message in messages:
        subject = message.get("subject")
        body_preview = message.get("bodyPreview")
        if not contains_query(query, subject, body_preview):
            continue

        results.append(
            MailSearchResult(
                id=message["id"],
                subject=subject,
                sender=email_address_name(message.get("from")),
                received_at=message.get("receivedDateTime"),
                body_preview=body_preview,
                web_link=message.get("webLink"),
            )
        )
        if len(results) >= limit:
            break

    return results