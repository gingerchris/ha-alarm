"""Binary sensor for Morning Alarm running status."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MorningAlarmCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MorningAlarmCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MorningAlarmRunningBinarySensor(coordinator)])


class MorningAlarmRunningBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """True while an alarm sequence is actively running."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_has_entity_name = True
    _attr_name = "Alarm active"
    _attr_icon = "mdi:alarm"

    def __init__(self, coordinator: MorningAlarmCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_alarm_running"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.config_entry.title,
            "manufacturer": "Morning Alarm",
        }

    @property
    def is_on(self) -> bool:
        return self.coordinator.alarm_running

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
