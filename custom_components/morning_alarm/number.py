"""Number entities for Morning Alarm — fade duration and brightness thresholds."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_FADE_DURATION,
    CONF_FINAL_BRIGHTNESS,
    CONF_FINAL_VOLUME,
    CONF_START_BRIGHTNESS,
    CONF_START_VOLUME,
    CONF_THRESHOLD_BRIGHTNESS,
    DEFAULT_FADE_DURATION,
    DEFAULT_FINAL_BRIGHTNESS,
    DEFAULT_FINAL_VOLUME,
    DEFAULT_START_BRIGHTNESS,
    DEFAULT_START_VOLUME,
    DEFAULT_THRESHOLD_BRIGHTNESS,
    DOMAIN,
)
from .coordinator import MorningAlarmCoordinator

_DESCRIPTIONS = [
    NumberEntityDescription(
        key=CONF_FADE_DURATION,
        name="Fade duration",
        icon="mdi:timer-outline",
        native_min_value=1,
        native_max_value=120,
        native_step=1,
        native_unit_of_measurement="min",
        mode=NumberMode.BOX,
    ),
    NumberEntityDescription(
        key=CONF_START_BRIGHTNESS,
        name="Start brightness",
        icon="mdi:brightness-1",
        native_min_value=1,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        mode=NumberMode.SLIDER,
    ),
    NumberEntityDescription(
        key=CONF_THRESHOLD_BRIGHTNESS,
        name="Threshold brightness",
        icon="mdi:brightness-4",
        native_min_value=1,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        mode=NumberMode.SLIDER,
    ),
    NumberEntityDescription(
        key=CONF_FINAL_BRIGHTNESS,
        name="Final brightness",
        icon="mdi:brightness-7",
        native_min_value=1,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        mode=NumberMode.SLIDER,
    ),
    NumberEntityDescription(
        key=CONF_START_VOLUME,
        name="Start volume",
        icon="mdi:volume-low",
        native_min_value=1,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        mode=NumberMode.SLIDER,
    ),
    NumberEntityDescription(
        key=CONF_FINAL_VOLUME,
        name="Final volume",
        icon="mdi:volume-high",
        native_min_value=1,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        mode=NumberMode.SLIDER,
    ),
]

_DEFAULTS: dict[str, float] = {
    CONF_FADE_DURATION: DEFAULT_FADE_DURATION,
    CONF_START_BRIGHTNESS: DEFAULT_START_BRIGHTNESS,
    CONF_THRESHOLD_BRIGHTNESS: DEFAULT_THRESHOLD_BRIGHTNESS,
    CONF_FINAL_BRIGHTNESS: DEFAULT_FINAL_BRIGHTNESS,
    CONF_START_VOLUME: DEFAULT_START_VOLUME,
    CONF_FINAL_VOLUME: DEFAULT_FINAL_VOLUME,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MorningAlarmCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MorningAlarmNumberEntity(coordinator, desc) for desc in _DESCRIPTIONS
    )


class MorningAlarmNumberEntity(CoordinatorEntity, NumberEntity):
    """A configurable numeric setting."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MorningAlarmCoordinator,
        description: NumberEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.config_entry.title,
            "manufacturer": "Morning Alarm",
        }

    @property
    def native_value(self) -> float:
        return float(
            self.coordinator.config_entry.options.get(
                self.entity_description.key,
                _DEFAULTS[self.entity_description.key],
            )
        )

    async def async_set_native_value(self, value: float) -> None:
        new_options = dict(self.coordinator.config_entry.options)
        new_options[self.entity_description.key] = int(value)
        self.hass.config_entries.async_update_entry(
            self.coordinator.config_entry, options=new_options
        )
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
