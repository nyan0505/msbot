from __future__ import annotations

from ._utils import build_date_range, contains_query, graph_datetime
from .graph_client import GraphClient
from .schemas import CalendarSearchResult


async def search_my_calendar(
    query: str,
    start_date: str,
    end_date: str,
    limit: int = 20,
) -> list[CalendarSearchResult]:
    start_dt, end_dt = build_date_range(start_date, end_date)
    fetch_size = min(max(limit * 3, limit), 100)

    params = {
        "startDateTime": graph_datetime(start_dt),
        "endDateTime": graph_datetime(end_dt),
        "$select": "id,subject,start,end,organizer,location,webLink",
        "$orderby": "start/dateTime",
        "$top": str(fetch_size),
    }

    async with GraphClient() as client:
        events = await client.get_all_pages("/me/calendarView", params=params, max_pages=3)

    results: list[CalendarSearchResult] = []
    for event in events:
        subject = event.get("subject")
        organizer = _get_organizer_name(event.get("organizer"))
        location = _get_location_name(event.get("location"))

        if not contains_query(query, subject, organizer, location):
            continue

        results.append(
            CalendarSearchResult(
                id=event["id"],
                subject=subject,
                start=(event.get("start") or {}).get("dateTime"),
                end=(event.get("end") or {}).get("dateTime"),
                organizer=organizer,
                location=location,
                web_link=event.get("webLink"),
            )
        )
        if len(results) >= limit:
            break

    return results


def _get_organizer_name(organizer: dict | None) -> str | None:
    if not isinstance(organizer, dict):
        return None
    email_address = organizer.get("emailAddress")
    if not isinstance(email_address, dict):
        return None
    return email_address.get("name") or email_address.get("address")


def _get_location_name(location: dict | None) -> str | None:
    if not isinstance(location, dict):
        return None
    return location.get("displayName") or location.get("address")