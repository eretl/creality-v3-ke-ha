"""Config flow for Creality Ender-3 V3 KE integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_MODE,
    CONF_BED_TEMP_OFFSET,
    CONF_NOZZLE_TEMP_OFFSET,
    MODE_WEBSOCKET,
    MODE_MOONRAKER,
    DEFAULT_PORT_WEBSOCKET,
    DEFAULT_PORT_MOONRAKER,
    DEFAULT_BED_TEMP_OFFSET,
    DEFAULT_NOZZLE_TEMP_OFFSET,
)
from .api import CrealityWebSocketAPI, CrealityMoonrakerAPI

_LOGGER = logging.getLogger(__name__)


class CrealityV3KEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Creality V3 KE."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1 — choose connection mode."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_MODE, default=MODE_WEBSOCKET): vol.In({
                        MODE_WEBSOCKET: "Native WebSocket — no extra software, port 9999",
                        MODE_MOONRAKER: "Moonraker API — Fluidd / Mainsail, port 7125",
                    }),
                }),
            )
        self._mode = user_input[CONF_MODE]
        return await self.async_step_connection()

    async def async_step_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2 — host, port, test connection."""
        default_port = (
            DEFAULT_PORT_WEBSOCKET if self._mode == MODE_WEBSOCKET
            else DEFAULT_PORT_MOONRAKER
        )
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]

            api = (
                CrealityWebSocketAPI(host, port)
                if self._mode == MODE_WEBSOCKET
                else CrealityMoonrakerAPI(host, port)
            )

            try:
                reachable = await api.async_test_connection()
            except Exception:
                reachable = False

            if not reachable:
                errors["base"] = "cannot_connect"
            else:
                self._host = host
                self._port = port
                return await self.async_step_offsets()

        return self.async_show_form(
            step_id="connection",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=default_port): vol.Coerce(int),
            }),
            errors=errors,
        )

    async def async_step_offsets(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3 — temperature correction offsets."""
        if user_input is not None:
            await self.async_set_unique_id(f"{self._host}:{self._port}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Creality V3 KE ({self._host})",
                data={
                    CONF_HOST: self._host,
                    CONF_PORT: self._port,
                    CONF_MODE: self._mode,
                    CONF_BED_TEMP_OFFSET: user_input[CONF_BED_TEMP_OFFSET],
                    CONF_NOZZLE_TEMP_OFFSET: user_input[CONF_NOZZLE_TEMP_OFFSET],
                },
            )

        return self.async_show_form(
            step_id="offsets",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_BED_TEMP_OFFSET,
                    default=DEFAULT_BED_TEMP_OFFSET,
                    description={"suggested_value": DEFAULT_BED_TEMP_OFFSET},
                ): vol.Coerce(float),
                vol.Required(
                    CONF_NOZZLE_TEMP_OFFSET,
                    default=DEFAULT_NOZZLE_TEMP_OFFSET,
                    description={"suggested_value": DEFAULT_NOZZLE_TEMP_OFFSET},
                ): vol.Coerce(float),
            }),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Allow editing offsets after setup via Configure button."""
        return CrealityOptionsFlow(config_entry)


class CrealityOptionsFlow(config_entries.OptionsFlow):
    """Options flow to adjust offsets without re-adding the integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_bed = self._entry.options.get(
            CONF_BED_TEMP_OFFSET,
            self._entry.data.get(CONF_BED_TEMP_OFFSET, DEFAULT_BED_TEMP_OFFSET),
        )
        current_nozzle = self._entry.options.get(
            CONF_NOZZLE_TEMP_OFFSET,
            self._entry.data.get(CONF_NOZZLE_TEMP_OFFSET, DEFAULT_NOZZLE_TEMP_OFFSET),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_BED_TEMP_OFFSET, default=current_bed): vol.Coerce(float),
                vol.Required(CONF_NOZZLE_TEMP_OFFSET, default=current_nozzle): vol.Coerce(float),
            }),
        )
