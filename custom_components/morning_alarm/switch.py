"""Switch entities for Morning Alarm — enable/disable per day."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DAY_NAMES, DAYS, DOMAIN, day_enabled_key
from .coordinator import MorningAlarmCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MorningAlarmCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MorningAlarmDaySwitch(coordinator, day) for day in DAYS
    )


class MorningAlarmDaySwitch(CoordinatorEntity, SwitchEntity):
    """Enable/disable alarm for a single day."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:alarm"
    _attr_has_entity_name = True

    def __init__(self, coordinator: MorningAlarmCoordinator, day: str) -> None:
        super().__init__(coordinator)
        self._day = day
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{day}_enabled"
        self._attr_name = f"{DAY_NAMES[day]} enabled"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.config_entry.title,
            "manufacturer": "Morning Alarm",
        }

    @property
    def is_on(self) -> bool:
        return bool(
            self.coordinator.config_entry.options.get(
                day_enabled_key(self._day), self._day not in ("sat", "sun")
            )
        )

    async def async_turn_on(self, **kwargs: object) -> None:
        await self._set_enabled(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        await self._set_enabled(False)

    async def _set_enabled(self, enabled: bool) -> None:
        new_options = dict(self.coordinator.config_entry.options)
        new_options[day_enabled_key(self._day)] = enabled
        self.hass.config_entries.async_update_entry(
            self.coordinator.config_entry, options=new_options
        )
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
