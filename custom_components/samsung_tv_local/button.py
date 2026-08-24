"""Button entities: one-tap launch of common apps."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LAUNCH_BUTTONS = [
    ("org.tizen.netflix", "Netflix"),
    ("11101200001", "YouTube"),
    ("3201512006785", "Prime Video"),
    ("3201901017640", "Disney+"),
    ("9Ur5IzDK1D", "Spotify"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SamsungAppButton(hub, app_id, label) for app_id, label in _LAUNCH_BUTTONS])


class SamsungAppButton(ButtonEntity):
    """Launch a specific app by id."""

    _attr_has_entity_name = True

    def __init__(self, hub, app_id: str, label: str) -> None:
        self._hub = hub
        self._app_id = app_id
        self._attr_unique_id = f"{hub.mac}-app-{app_id}"
        self._attr_translation_key = "launch_app"
        self._attr_translation_placeholders = {"app": label}
        self._attr_device_info = {
            "identifiers": {(DOMAIN, hub.mac)},
            "name": hub.name,
            "manufacturer": "Samsung",
            "model": "QN90B",
        }

    async def async_press(self) -> None:
        await self._hub.launch_app(self._app_id)
