"""The {instance_name} placeholder follows Home Assistant's language (issue #533)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


def _name(hass: HomeAssistant, entry, state_key: str) -> str | None:
    (match,) = (
        e
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if e.unique_id.endswith(f"_{state_key}")
    )
    return match.original_name


async def test_instance_names_are_localized(
    hass: HomeAssistant, mock_entry, mock_coordinator_session
) -> None:
    hass.config.language = "de"
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    assert _name(hass, mock_entry, "freezer_temperature") == "Gefrierschrank Temperatur"
    assert _name(hass, mock_entry, "icemaker_one_enabled") == "Eiswürfel aktiviert"


async def test_instance_names_stay_english_by_default(
    hass: HomeAssistant, mock_entry, mock_coordinator_session
) -> None:
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    assert _name(hass, mock_entry, "freezer_temperature") == "Freezer temperature"
    assert _name(hass, mock_entry, "icemaker_one_enabled") == "Cubed ice enabled"
