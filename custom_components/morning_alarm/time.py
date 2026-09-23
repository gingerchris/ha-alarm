"""Time entities for Morning Alarm — one per day of week."""
from __future__ import annotations

from datetime import time as time_type

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DAY_NAMES, DAYS, DOMAIN, day_time_key
from .coordinator import MorningAlarmCoordinator

_DEFAULT_TIME = time_type(7, 0)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MorningAlarmCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MorningAlarmTimeEntity(coordinator, day) for day in DAYS
    )


class MorningAlarmTimeEntity(CoordinatorEntity, TimeEntity):
    """Alarm time for a single day of the week."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:clock-outline"
    _attr_has_entity_name = True

    def __init__(self, coordinator: MorningAlarmCoordinator, day: str) -> None:
        super().__init__(coordinator)
        self._day = day
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{day}_time"
        self._attr_name = f"{DAY_NAMES[day]} alarm time"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.config_entry.title,
            "manufacturer": "Morning Alarm",
        }

    @property
    def native_value(self) -> time_type | None:
        time_str = self.coordinator.config_entry.options.get(
            day_time_key(self._day), "07:00"
        )
        try:
            parts = time_str.split(":")
            return time_type(int(parts[0]), int(parts[1]))
        except (ValueError, AttributeError, IndexError):
            return _DEFAULT_TIME

    async def async_set_value(self, value: time_type) -> None:
        new_options = dict(self.coordinator.config_entry.options)
        new_options[day_time_key(self._day)] = value.strftime("%H:%M")
        self.hass.config_entries.async_update_entry(
            self.coordinator.config_entry, options=new_options
        )
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
