"""Samsung TV Local (QN90B): local WebSocket control without SmartThings."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_MAC, CONF_NAME, CONF_TOKEN, DOMAIN, PLATFORMS
from .coordinator import SamsungTvHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    async def _save_token(token: str) -> None:
        hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_TOKEN: token})

    hub = SamsungTvHub(
        hass,
        host=entry.data[CONF_HOST],
        mac=entry.data[CONF_MAC],
        token=entry.data[CONF_TOKEN],
        name=entry.data.get(CONF_NAME, "Samsung TV"),
        token_saver=_save_token,
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
