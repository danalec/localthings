"""Media player entity for a locally controlled Samsung QN90B TV."""

from __future__ import annotations

import datetime
import logging

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KNOWN_APPS

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = datetime.timedelta(seconds=30)

# Reverse map so play_media accepts either an app id or a friendly name.
_APP_ID_BY_NAME = {name: app_id for app_id, name in KNOWN_APPS.items()}

SUPPORT_SAMSUNGTV = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.PLAY_MEDIA
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SamsungTvMediaPlayer(hub)], update_before_add=False)


class SamsungTvMediaPlayer(MediaPlayerEntity):
    """A QN90B controlled over the local WebSocket remote."""

    _attr_has_entity_name = True
    _attr_supported_features = SUPPORT_SAMSUNGTV

    def __init__(self, hub) -> None:
        self._hub = hub
        self._attr_unique_id = f"{hub.mac}-media_player"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, hub.mac)},
            "name": hub.name,
            "manufacturer": "Samsung",
            "model": "QN90B",
        }
        self._sources: list[str] = []
        self._volume = 0
        self._muted = False
        self._state = STATE_OFF

    async def async_update(self) -> None:
        """Refresh on/off, volume and sources from the TV."""
        try:
            if not await self._hub.is_on():
                self._state = STATE_OFF
                return
            self._state = STATE_ON
            vol = await self._hub.volume()
            if vol:
                self._volume = int(vol.get("volume") or 0)
                self._hub.max_volume = int(vol.get("max") or 0)
                self._muted = bool(vol.get("mute"))
            sources = await self._hub.sources()
            if sources:
                self._sources = [s.get("name") or s.get("id") for s in sources]
        except Exception as exc:
            _LOGGER.debug("update failed: %s", exc)
            self._state = STATE_OFF

    @property
    def state(self) -> str:
        return self._state

    @property
    def volume_level(self) -> float | None:
        if self._hub.max_volume:
            return self._volume / self._hub.max_volume
        return None

    @property
    def is_volume_muted(self) -> bool:
        return self._muted

    @property
    def source_list(self) -> list[str]:
        return self._sources

    async def async_turn_on(self) -> None:
        await self._hub.turn_on()

    async def async_turn_off(self) -> None:
        await self._hub.turn_off()

    async def async_volume_up(self) -> None:
        await self._hub.send_key("KEY_VOLUP")

    async def async_volume_down(self) -> None:
        await self._hub.send_key("KEY_VOLDOWN")

    async def async_volume_set(self, volume: float) -> None:
        if not self._hub.max_volume:
            return
        target = round(volume * self._hub.max_volume)
        await self._hub.volume_step(target - self._volume)
        self._volume = target

    async def async_mute_volume(self, mute: bool) -> None:
        if self._muted != mute:
            await self._hub.send_key("KEY_MUTE")
            self._muted = mute

    async def async_select_source(self, source: str) -> None:
        await self._hub.set_source(source)

    async def async_play_media(self, media_type: str, media_id: str, **kwargs) -> None:
        if media_type != "app":
            _LOGGER.warning("only media_type 'app' is supported (got %s)", media_type)
            return
        app_id = KNOWN_APPS.get(media_id) or _APP_ID_BY_NAME.get(media_id) or media_id
        await self._hub.launch_app(app_id)

    async def async_media_play(self) -> None:
        await self._hub.send_key("KEY_PLAY")

    async def async_media_pause(self) -> None:
        await self._hub.send_key("KEY_PAUSE")

    async def async_media_stop(self) -> None:
        await self._hub.send_key("KEY_STOP")

    async def async_media_next_track(self) -> None:
        await self._hub.send_key("KEY_FF")

    async def async_media_previous_track(self) -> None:
        await self._hub.send_key("KEY_REW")
