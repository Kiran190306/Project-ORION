"""Timezone-aware trading-session resolution."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .models import TradingSession


class SessionManager:
    """Resolve active sessions using local trading windows and IANA timezones."""

    def __init__(self, sessions: tuple[TradingSession, ...] = ()) -> None:
        self._sessions: dict[str, TradingSession] = {
            session.session_id: session for session in sessions
        }
        self._lock = asyncio.Lock()

    async def register(self, session: TradingSession) -> None:
        """Add or replace a trading session by its stable identifier."""
        async with self._lock:
            self._sessions[session.session_id] = session

    async def active_sessions(self, instant: datetime) -> tuple[TradingSession, ...]:
        """Return sessions active at an aware UTC instant.

        Raises:
            ValueError: If ``instant`` is timezone-naive.
        """
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("instant must be timezone-aware")
        utc_instant = instant.astimezone(timezone.utc)
        async with self._lock:
            sessions = tuple(self._sessions.values())
        active = [session for session in sessions if self._is_active(session, utc_instant)]
        return tuple(sorted(active, key=lambda session: session.session_id))

    @staticmethod
    def _is_active(session: TradingSession, instant: datetime) -> bool:
        """Determine whether a UTC instant falls inside one local session window."""
        try:
            local = instant.astimezone(ZoneInfo(session.timezone_name))
        except Exception:
            # Fallback for runtimes without tzdata: treat timezone windows as UTC.
            local = instant.astimezone(timezone.utc)
        local_time = local.timetz().replace(tzinfo=None)

        weekday = local.weekday()
        if session.start_time < session.end_time:
            return (
                weekday in session.trading_days
                and session.start_time <= local_time < session.end_time
            )
        prior_weekday = (weekday - 1) % 7
        return (weekday in session.trading_days and local_time >= session.start_time) or (
            prior_weekday in session.trading_days and local_time < session.end_time
        )
