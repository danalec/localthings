"""Remote entity: send arbitrary keys to the TV."""

from __future__ import annotations

from homeassistant.components.remote import RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEYS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SamsungTvRemote(hub)])


class SamsungTvRemote(RemoteEntity):
    """Send any remote key (friendly name or raw KEY_* code)."""

    _attr_has_entity_name = True

    def __init__(self, hub) -> None:
        self._hub = hub
        self._attr_unique_id = f"{hub.mac}-remote"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, hub.mac)},
            "name": hub.name,
            "manufacturer": "Samsung",
            "model": "QN90B",
        }

    async def async_send_command(self, command: list[str], **kwargs) -> None:
        for cmd in command:
            code = KEYS.get(cmd, cmd)
            await self._hub.send_key(code)
