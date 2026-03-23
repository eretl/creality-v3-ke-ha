"""Creality Ender-3 V3 KE Home Assistant Integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_MODE,
    CONF_BED_TEMP_OFFSET,
    CONF_NOZZLE_TEMP_OFFSET,
    MODE_WEBSOCKET,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_BED_TEMP_OFFSET,
    DEFAULT_NOZZLE_TEMP_OFFSET,
)
from .api import CrealityWebSocketAPI, CrealityMoonrakerAPI

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    mode = entry.data[CONF_MODE]

    # Read offsets — prefer options (editable after setup) over original data
    bed_offset = entry.options.get(
        CONF_BED_TEMP_OFFSET,
        entry.data.get(CONF_BED_TEMP_OFFSET, DEFAULT_BED_TEMP_OFFSET),
    )
    nozzle_offset = entry.options.get(
        CONF_NOZZLE_TEMP_OFFSET,
        entry.data.get(CONF_NOZZLE_TEMP_OFFSET, DEFAULT_NOZZLE_TEMP_OFFSET),
    )

    api = (
        CrealityWebSocketAPI(host, port, bed_offset=bed_offset, nozzle_offset=nozzle_offset)
        if mode == MODE_WEBSOCKET
        else CrealityMoonrakerAPI(host, port, bed_offset=bed_offset, nozzle_offset=nozzle_offset)
    )

    coordinator = CrealityDataUpdateCoordinator(hass, api, entry.title)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Re-load when options (offsets) change
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class CrealityDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api, name: str) -> None:
        super().__init__(
            hass, _LOGGER, name=name,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        try:
            return await self.api.async_get_data()
        except Exception as err:
            raise UpdateFailed(f"Printer communication error: {err}") from err
