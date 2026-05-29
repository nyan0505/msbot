from __future__ import annotations

import html
import re
from datetime import UTC, date, datetime, time


def build_date_range(start_date: str, end_date: str) -> tuple[datetime, datetime]:
    start_dt = parse_iso_datetime(start_date, end_of_day=False)
    end_dt = parse_iso_datetime(end_date, end_of_day=True)
    if end_dt < start_dt:
        raise ValueError("end_date must be the same as or later than start_date")
    return start_dt, end_dt


def parse_iso_datetime(value: str, end_of_day: bool) -> datetime:
    raw = value.strip()
    if not raw:
        raise ValueError("Date value is required")

    if "T" not in raw and len(raw) <= 10:
        parsed_date = date.fromisoformat(raw)
        dt = datetime.combine(parsed_date, time.max if end_of_day else time.min)
    else:
        normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(normalized)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.astimezone(UTC)


def graph_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def is_within_range(value: str | None, start_dt: datetime, end_dt: datetime) -> bool:
    if not value:
        return False
    dt = parse_iso_datetime(value, end_of_day=False)
    return start_dt <= dt <= end_dt


def contains_query(query: str, *parts: str | None) -> bool:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return True

    haystack = " ".join(part for part in parts if part).lower()
    return normalized_query in haystack


def strip_html(value: str | None) -> str:
    if not value:
        return ""

    without_tags = re.sub(r"<[^>]+>", " ", value)
    plain_text = html.unescape(without_tags)
    return re.sub(r"\s+", " ", plain_text).strip()


def make_snippet(value: str, query: str, width: int = 160) -> str:
    clean_text = re.sub(r"\s+", " ", value).strip()
    if not clean_text:
        return ""

    normalized_query = query.strip().lower()
    if not normalized_query:
        return clean_text[:width]

    match_index = clean_text.lower().find(normalized_query)
    if match_index < 0:
        return clean_text[:width]

    start = max(match_index - width // 3, 0)
    end = min(start + width, len(clean_text))
    start = max(end - width, 0)
    snippet = clean_text[start:end].strip()

    if start > 0:
        snippet = f"...{snippet}"
    if end < len(clean_text):
        snippet = f"{snippet}..."

    return snippet


def email_address_name(address: dict | None) -> str | None:
    if not isinstance(address, dict):
        return None

    email_address = address.get("emailAddress")
    if isinstance(email_address, dict):
        return email_address.get("name") or email_address.get("address")

    return None