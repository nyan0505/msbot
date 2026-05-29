"""Read-only Microsoft 365 integration layer for delegated user access."""

from .auth import get_access_token
from .calendar import search_my_calendar
from .mail import search_my_outlook_mail
from .schemas import CalendarSearchResult, MailSearchResult, TeamsSearchResult
from .teams import search_my_teams_chats

__all__ = [
    "CalendarSearchResult",
    "MailSearchResult",
    "TeamsSearchResult",
    "get_access_token",
    "search_my_calendar",
    "search_my_outlook_mail",
    "search_my_teams_chats",
]