"""Binary sensor platform for Creality Ender-3 V3 KE."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CrealityDataUpdateCoordinator
from .const import DOMAIN, KEY_STATUS, KEY_ONLINE


@dataclass(frozen=True)
class CrealityBinarySensorDesc(BinarySensorEntityDescription):
    is_on_fn: Callable[[dict], bool] = lambda _: False


BINARY_SENSORS: tuple[CrealityBinarySensorDesc, ...] = (
    CrealityBinarySensorDesc(
        key="is_printing",
        name="Printing",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:printer-3d-nozzle",
        is_on_fn=lambda d: d.get(KEY_STATUS) == "printing",
    ),
    CrealityBinarySensorDesc(
        key="is_paused",
        name="Paused",
        icon="mdi:pause-circle-outline",
        is_on_fn=lambda d: d.get(KEY_STATUS) == "paused",
    ),
    CrealityBinarySensorDesc(
        key="has_error",
        name="Printer Error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert-circle-outline",
        is_on_fn=lambda d: d.get(KEY_STATUS) == "error",
    ),
    CrealityBinarySensorDesc(
        key="is_online",
        name="Printer Online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:wifi-check",
        is_on_fn=lambda d: bool(d.get(KEY_ONLINE)),
    ),
    CrealityBinarySensorDesc(
        key="bed_heating",
        name="Bed Heating",
        device_class=BinarySensorDeviceClass.HEAT,
        icon="mdi:radiator",
        is_on_fn=lambda d: float(d.get("bed_target", 0) or 0) > 0,
    ),
    CrealityBinarySensorDesc(
        key="extruder_heating",
        name="Extruder Heating",
        device_class=BinarySensorDeviceClass.HEAT,
        icon="mdi:fire",
        is_on_fn=lambda d: float(d.get("extruder_target", 0) or 0) > 0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CrealityDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        CrealityBinarySensor(coordinator, desc, entry) for desc in BINARY_SENSORS
    )


class CrealityBinarySensor(CoordinatorEntity, BinarySensorEntity):
    entity_description: CrealityBinarySensorDesc

    def __init__(self, coordinator, description: CrealityBinarySensorDesc, entry: ConfigEntry) -> None:
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
    def is_on(self) -> bool:
        data = self.coordinator.data or {}
        return self.entity_description.is_on_fn(data)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success
