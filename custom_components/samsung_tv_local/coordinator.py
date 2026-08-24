"""Coordinator: owns the local TV session and exposes control helpers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from homeassistant.core import HomeAssistant

from .protocol import AuthError, SamsungRemote, pair, wake_on_lan

_LOGGER = logging.getLogger(__name__)


class SamsungTvHub:
    """Controller for one TV over the local WebSocket protocol.

    The auth token is refreshed automatically (re-paired) whenever the TV
    rejects it, so a token expiry never leaves the TV stuck.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        mac: str,
        token: str,
        name: str = "Samsung TV",
        token_saver: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self.hass = hass
        self.host = host
        self.mac = mac
        self.token = token
        self.name = name
        self.max_volume = 0
        self._token_saver = token_saver
        self._token_lock = asyncio.Lock()

    async def _refresh_token(self) -> None:
        """Re-pair with the TV and persist the fresh token."""
        old_token = self.token
        async with self._token_lock:
            # Another task may have refreshed while we waited for the lock.
            if self.token != old_token:
                return
            token = await pair(self.host, name="LocalThings")
            self.token = token
            if self._token_saver is not None:
                await self._token_saver(token)
            _LOGGER.info("refreshed TV auth token")

    async def _session(self) -> SamsungRemote:
        """Open a session, refreshing the token once if it was rejected."""
        tv = SamsungRemote(self.host, name="LocalThings", token=self.token)
        try:
            await tv.connect()
        except AuthError:
            await self._refresh_token()
            tv = SamsungRemote(self.host, name="LocalThings", token=self.token)
            await tv.connect()
        return tv

    async def is_on(self) -> bool:
        try:
            tv = await self._session()
            await tv.close()
            return True
        except Exception:
            return False

    async def turn_on(self) -> None:
        if not await self.is_on():
            await wake_on_lan(self.mac, self.host)

    async def _send_key_authed(self, key: str) -> None:
        """Send a key, refreshing the token and retrying on auth rejection."""
        for attempt in (1, 2):
            tv = await self._session()  # refreshes on connect-time rejection
            try:
                await tv.send_key_checked(key)  # detects command-time rejection
                return
            except AuthError:
                await tv.close()
                if attempt == 1:
                    await self._refresh_token()
                    continue
                raise
            finally:
                await tv.close()

    async def turn_off(self) -> None:
        await self._send_key_authed("KEY_POWER")

    async def send_key(self, key: str) -> None:
        await self._send_key_authed(key)

    async def volume_step(self, delta: int) -> None:
        """Move the volume by `delta` steps on a single session."""
        if delta == 0:
            return
        key = "KEY_VOLUP" if delta > 0 else "KEY_VOLDOWN"
        async with await self._session() as tv:
            for _ in range(abs(delta)):
                await tv.send_key(key)

    async def volume(self) -> dict:
        try:
            async with await self._session() as tv:
                return await tv.get_volume()
        except Exception as exc:
            _LOGGER.debug("volume query failed: %s", exc)
            return {}

    async def sources(self) -> list:
        try:
            async with await self._session() as tv:
                return await tv.get_sources()
        except Exception as exc:
            _LOGGER.debug("sources query failed: %s", exc)
            return []

    async def launch_app(self, app_id: str) -> None:
        async with await self._session() as tv:
            await tv.launch_app(app_id)

    async def set_source(self, source_id: str) -> None:
        """Best-effort direct source switch.

        Not every Tizen firmware answers `ed.setSource`; fall back to cycling
        with KEY_SOURCE when it is ignored.
        """
        tv = await self._session()
        try:
            await tv.set_source(source_id)
        except Exception as exc:
            _LOGGER.warning("ed.setSource failed (%s); cycling KEY_SOURCE", exc)
            await tv.send_key("KEY_SOURCE")
        finally:
            await tv.close()
