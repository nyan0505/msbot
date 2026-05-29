from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MailSearchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    subject: str | None = None
    sender: str | None = None
    received_at: str | None = None
    body_preview: str | None = None
    web_link: str | None = None


class TeamsSearchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chat_id: str
    message_id: str
    created_at: str | None = None
    sender: str | None = None
    participants: list[str]
    snippet: str
    web_url: str | None = None


class CalendarSearchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    subject: str | None = None
    start: str | None = None
    end: str | None = None
    organizer: str | None = None
    location: str | None = None
    web_link: str | None = None