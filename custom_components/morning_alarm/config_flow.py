"""Config flow for Morning Alarm."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_DIMMABLE_LIGHTS,
    CONF_FADE_DURATION,
    CONF_FINAL_BRIGHTNESS,
    CONF_MEDIA_CONTENT_ID,
    CONF_MEDIA_PLAYER,
    CONF_ONOFF_LIGHTS,
    CONF_START_BRIGHTNESS,
    CONF_THRESHOLD_BRIGHTNESS,
    DAYS,
    DEFAULT_ALARM_TIME,
    DEFAULT_FADE_DURATION,
    DEFAULT_FINAL_BRIGHTNESS,
    DEFAULT_SAT_TIME,
    DEFAULT_START_BRIGHTNESS,
    DEFAULT_SUN_TIME,
    DEFAULT_THRESHOLD_BRIGHTNESS,
    DOMAIN,
    day_enabled_key,
    day_time_key,
)

_DEFAULT_TIMES: dict[str, str] = {
    "mon": "07:00",
    "tue": "07:30",
    "wed": "07:00",
    "thu": "07:30",
    "fri": "07:00",
    "sat": DEFAULT_SAT_TIME,
    "sun": DEFAULT_SUN_TIME,
}


def _audio_schema(defaults: dict[str, Any]) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if defaults.get(CONF_MEDIA_PLAYER):
        fields[vol.Optional(CONF_MEDIA_PLAYER, default=defaults[CONF_MEDIA_PLAYER])] = (
            selector.EntitySelector(selector.EntitySelectorConfig(domain="media_player"))
        )
    else:
        fields[vol.Optional(CONF_MEDIA_PLAYER)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="media_player")
        )
    fields[vol.Optional(CONF_MEDIA_CONTENT_ID, default=defaults.get(CONF_MEDIA_CONTENT_ID, ""))] = (
        selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT))
    )
    return vol.Schema(fields)


def _lights_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_DIMMABLE_LIGHTS,
                default=defaults.get(CONF_DIMMABLE_LIGHTS, []),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light", multiple=True)
            ),
            vol.Optional(
                CONF_ONOFF_LIGHTS,
                default=defaults.get(CONF_ONOFF_LIGHTS, []),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light", multiple=True)
            ),
        }
    )


def _brightness_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_FADE_DURATION,
                default=int(defaults.get(CONF_FADE_DURATION, DEFAULT_FADE_DURATION)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=120,
                    step=1,
                    unit_of_measurement="min",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Optional(
                CONF_START_BRIGHTNESS,
                default=int(defaults.get(CONF_START_BRIGHTNESS, DEFAULT_START_BRIGHTNESS)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Optional(
                CONF_THRESHOLD_BRIGHTNESS,
                default=int(defaults.get(CONF_THRESHOLD_BRIGHTNESS, DEFAULT_THRESHOLD_BRIGHTNESS)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Optional(
                CONF_FINAL_BRIGHTNESS,
                default=int(defaults.get(CONF_FINAL_BRIGHTNESS, DEFAULT_FINAL_BRIGHTNESS)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
        }
    )


def _schedule_schema(defaults: dict[str, Any]) -> vol.Schema:
    fields: dict[Any, Any] = {}
    for day in DAYS:
        default_enabled = day not in ("sat", "sun")
        default_time = _DEFAULT_TIMES.get(day, DEFAULT_ALARM_TIME)
        fields[vol.Optional(day_enabled_key(day), default=defaults.get(day_enabled_key(day), default_enabled))] = (
            selector.BooleanSelector()
        )
        fields[vol.Optional(day_time_key(day), default=defaults.get(day_time_key(day), default_time))] = (
            selector.TimeSelector()
        )
    return vol.Schema(fields)


def _normalise_options(data: dict[str, Any]) -> dict[str, Any]:
    """Normalise time strings to HH:MM and brightness values to int."""
    out = dict(data)
    out.setdefault(CONF_MEDIA_PLAYER, "")
    out.setdefault(CONF_MEDIA_CONTENT_ID, "")
    for day in DAYS:
        key = day_time_key(day)
        if key in out:
            out[key] = str(out[key])[:5]
    for key in (CONF_FADE_DURATION, CONF_START_BRIGHTNESS, CONF_THRESHOLD_BRIGHTNESS, CONF_FINAL_BRIGHTNESS):
        if key in out:
            out[key] = int(out[key])
    return out


class MorningAlarmConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Morning Alarm."""

    VERSION = 1

    def __init__(self) -> None:
        self._options: dict[str, Any] = {}
        self._title: str = "Morning Alarm"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._title = user_input.get("title", "Morning Alarm")
            return await self.async_step_audio()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("title", default="Morning Alarm"): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                }
            ),
        )

    async def async_step_audio(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_lights()

        return self.async_show_form(
            step_id="audio",
            data_schema=_audio_schema(self._options),
        )

    async def async_step_lights(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_brightness()

        return self.async_show_form(
            step_id="lights",
            data_schema=_lights_schema(self._options),
        )

    async def async_step_brightness(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_schedule()

        return self.async_show_form(
            step_id="brightness",
            data_schema=_brightness_schema(self._options),
        )

    async def async_step_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return self.async_create_entry(
                title=self._title,
                data={},
                options=_normalise_options(self._options),
            )

        return self.async_show_form(
            step_id="schedule",
            data_schema=_schedule_schema(self._options),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MorningAlarmOptionsFlow(config_entry)


class MorningAlarmOptionsFlow(OptionsFlow):
    """Handle an options flow for Morning Alarm."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
        self._options: dict[str, Any] = dict(config_entry.options)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return await self.async_step_audio()

    async def async_step_audio(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_lights()

        return self.async_show_form(
            step_id="audio",
            data_schema=_audio_schema(self._options),
        )

    async def async_step_lights(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_brightness()

        return self.async_show_form(
            step_id="lights",
            data_schema=_lights_schema(self._options),
        )

    async def async_step_brightness(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_schedule()

        return self.async_show_form(
            step_id="brightness",
            data_schema=_brightness_schema(self._options),
        )

    async def async_step_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return self.async_create_entry(
                data=_normalise_options(self._options),
            )

        return self.async_show_form(
            step_id="schedule",
            data_schema=_schedule_schema(self._options),
        )
