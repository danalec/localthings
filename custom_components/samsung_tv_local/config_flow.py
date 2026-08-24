"""Config flow for Samsung TV Local (QN90B).

Two ways to authenticate:
  * provide an existing token directly (e.g. the one from the stock HA
    `samsungtv` integration entry - the pragmatic path), or
  * pair by allowing the TV's on-screen popup (QN90B firmware grants the
    token in the channel-connect event, no PIN required).
"""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import CONF_HOST, CONF_MAC, CONF_TOKEN, DOMAIN
from .protocol import pair

_LOGGER = logging.getLogger(__name__)

_TEXT = TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT))

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): _TEXT,
        vol.Required(CONF_MAC): _TEXT,
        vol.Optional(CONF_NAME, default="Samsung TV"): _TEXT,
        vol.Optional(CONF_TOKEN, default=""): _TEXT,
    }
)


class SamsungTvLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Samsung TV Local config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_MAC].lower())
            self._abort_if_unique_id_configured()
            self._host = user_input[CONF_HOST]
            self._mac = user_input[CONF_MAC]
            self._name = user_input.get(CONF_NAME, "Samsung TV")
            token = user_input.get(CONF_TOKEN) or ""
            if token:
                return self.async_create_entry(
                    title=self._name,
                    data={
                        CONF_HOST: self._host,
                        CONF_MAC: self._mac,
                        CONF_TOKEN: token,
                        CONF_NAME: self._name,
                    },
                )
            return await self.async_step_pairing()
        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)

    async def async_step_pairing(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                token = await pair(self._host, name="LocalThings")
            except Exception as exc:
                _LOGGER.warning("pairing failed: %s", exc)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=self._name,
                    data={
                        CONF_HOST: self._host,
                        CONF_MAC: self._mac,
                        CONF_TOKEN: token,
                        CONF_NAME: self._name,
                    },
                )
        return self.async_show_form(step_id="pairing", data_schema=vol.Schema({}), errors=errors)
