from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Sequence

from .calendar import search_my_calendar
from .mail import search_my_outlook_mail
from .teams import search_my_teams_chats


def _prompt(label: str) -> str:
    return input(f"{label}: ").strip()


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m ms365.demo_cli")
    parser.add_argument("--source", choices=["mail", "teams", "calendar"])
    parser.add_argument("--query")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--limit-per-chat", type=int, default=50)
    parser.add_argument("--max-chats", type=int, default=20)
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> None:
    source = args.source or _prompt("Source (mail/teams/calendar)")
    query = args.query or _prompt("Query")
    start_date = args.start_date or _prompt("Start date (ISO)")
    end_date = args.end_date or _prompt("End date (ISO)")

    if source == "mail":
        results = await search_my_outlook_mail(query, start_date, end_date, limit=args.limit)
    elif source == "teams":
        results = await search_my_teams_chats(
            query,
            start_date,
            end_date,
            limit_per_chat=args.limit_per_chat,
            max_chats=args.max_chats,
        )
    elif source == "calendar":
        results = await search_my_calendar(query, start_date, end_date, limit=args.limit)
    else:
        raise ValueError("Source must be one of: mail, teams, calendar")

    if not results:
        print("No results found.")
        return

    for index, item in enumerate(results, start=1):
        print(f"\n[{index}]")
        for key, value in item.model_dump().items():
            if isinstance(value, list):
                rendered = ", ".join(value)
            else:
                rendered = value
            print(f"{key}: {rendered}")


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()