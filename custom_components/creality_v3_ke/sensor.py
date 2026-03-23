"""Sensor platform for Creality Ender-3 V3 KE."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CrealityDataUpdateCoordinator
from .const import (
    DOMAIN,
    KEY_BED_TARGET,
    KEY_BED_TEMP,
    KEY_EXTRUDER_TARGET,
    KEY_EXTRUDER_TEMP,
    KEY_FAN_SPEED,
    KEY_FILENAME,
    KEY_FLOW_RATE,
    KEY_LAYER_CURRENT,
    KEY_LAYER_TOTAL,
    KEY_PRINT_SPEED,
    KEY_PRINT_TIME,
    KEY_PRINT_TIME_LEFT,
    KEY_PROGRESS,
    KEY_RAW_DATA,
    KEY_STATUS,
)


@dataclass(frozen=True)
class CrealitySensorDesc(SensorEntityDescription):
    data_key: str = ""


SENSORS: tuple[CrealitySensorDesc, ...] = (
    CrealitySensorDesc(
        key="status", data_key=KEY_STATUS,
        name="Print Status",
        icon="mdi:printer-3d",
    ),
    CrealitySensorDesc(
        key="extruder_temp", data_key=KEY_EXTRUDER_TEMP,
        name="Extruder Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
    ),
    CrealitySensorDesc(
        key="extruder_target", data_key=KEY_EXTRUDER_TARGET,
        name="Extruder Target Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer-chevron-up",
    ),
    CrealitySensorDesc(
        key="bed_temp", data_key=KEY_BED_TEMP,
        name="Bed Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
    ),
    CrealitySensorDesc(
        key="bed_target", data_key=KEY_BED_TARGET,
        name="Bed Target Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer-chevron-up",
    ),
    CrealitySensorDesc(
        key="progress", data_key=KEY_PROGRESS,
        name="Print Progress",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:progress-clock",
    ),
    CrealitySensorDesc(
        key="print_time", data_key=KEY_PRINT_TIME,
        name="Print Time Elapsed",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer",
    ),
    CrealitySensorDesc(
        key="print_time_left", data_key=KEY_PRINT_TIME_LEFT,
        name="Print Time Remaining",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer-sand",
    ),
    CrealitySensorDesc(
        key="filename", data_key=KEY_FILENAME,
        name="Current File",
        icon="mdi:file-outline",
    ),
    CrealitySensorDesc(
        key="fan_speed", data_key=KEY_FAN_SPEED,
        name="Fan Speed",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
    ),
    CrealitySensorDesc(
        key="print_speed", data_key=KEY_PRINT_SPEED,
        name="Print Speed",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
    ),
    CrealitySensorDesc(
        key="flow_rate", data_key=KEY_FLOW_RATE,
        name="Flow Rate",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-percent",
    ),
    CrealitySensorDesc(
        key="layer_current", data_key=KEY_LAYER_CURRENT,
        name="Current Layer",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:layers",
    ),
    CrealitySensorDesc(
        key="layer_total", data_key=KEY_LAYER_TOTAL,
        name="Total Layers",
        icon="mdi:layers-triple",
    ),
    # ── Diagnostic sensor — shows all raw keys the printer sends ────────────
    # Use this to find the exact field names your firmware version uses.
    # In HA: Developer Tools → States → filter "raw_data"
    CrealitySensorDesc(
        key="raw_data", data_key=KEY_RAW_DATA,
        name="Raw Data (Diagnostic)",
        icon="mdi:code-json",
        entity_registry_enabled_default=False,   # disabled by default; enable in HA UI
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CrealityDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        CrealitySensor(coordinator, desc, entry) for desc in SENSORS
    )


class CrealitySensor(CoordinatorEntity, SensorEntity):
    entity_description: CrealitySensorDesc

    def __init__(
        self,
        coordinator: CrealityDataUpdateCoordinator,
        description: CrealitySensorDesc,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Creality",
            model="Ender-3 V3 KE",
        )

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data or {}
        return data.get(self.entity_description.data_key)

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        return bool((self.coordinator.data or {}).get("online", False))
