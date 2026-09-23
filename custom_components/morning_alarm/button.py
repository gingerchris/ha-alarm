"""Button entities for Morning Alarm — test and stop."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
    async_add_entities(
        [
            MorningAlarmTestButton(coordinator),
            MorningAlarmStopButton(coordinator),
        ]
    )


class MorningAlarmTestButton(CoordinatorEntity, ButtonEntity):
    """Immediately run the alarm sequence for testing."""

    _attr_icon = "mdi:alarm-check"
    _attr_has_entity_name = True
    _attr_name = "Test alarm"

    def __init__(self, coordinator: MorningAlarmCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_test_alarm"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.config_entry.title,
            "manufacturer": "Morning Alarm",
        }

    async def async_press(self) -> None:
        await self.coordinator.async_run_alarm()


class MorningAlarmStopButton(CoordinatorEntity, ButtonEntity):
    """Stop a running alarm sequence."""

    _attr_icon = "mdi:alarm-off"
    _attr_has_entity_name = True
    _attr_name = "Stop alarm"

    def __init__(self, coordinator: MorningAlarmCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_stop_alarm"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.config_entry.title,
            "manufacturer": "Morning Alarm",
        }

    async def async_press(self) -> None:
        await self.coordinator.async_stop_alarm()
