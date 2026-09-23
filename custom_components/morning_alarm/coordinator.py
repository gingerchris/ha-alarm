"""Morning Alarm coordinator: scheduling, alarm sequence, and state."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.light import ColorMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DIMMABLE_LIGHTS,
    CONF_FADE_DURATION,
    CONF_FINAL_BRIGHTNESS,
    CONF_FINAL_VOLUME,
    CONF_MEDIA_CONTENT_ID,
    CONF_MEDIA_PLAYER,
    CONF_ONOFF_LIGHTS,
    CONF_START_BRIGHTNESS,
    CONF_START_VOLUME,
    CONF_THRESHOLD_BRIGHTNESS,
    DAY_NAMES,
    DAY_WEEKDAY,
    DAYS,
    DEFAULT_ALARM_TIME,
    DEFAULT_FADE_DURATION,
    DEFAULT_FINAL_BRIGHTNESS,
    DEFAULT_FINAL_VOLUME,
    DEFAULT_START_BRIGHTNESS,
    DEFAULT_START_VOLUME,
    DEFAULT_THRESHOLD_BRIGHTNESS,
    DOMAIN,
    FADE_STEP_INTERVAL,
    day_enabled_key,
    day_time_key,
)

_LOGGER = logging.getLogger(__name__)

_BRIGHTNESS_COLOR_MODES = {
    ColorMode.BRIGHTNESS,
    ColorMode.COLOR_TEMP,
    ColorMode.HS,
    ColorMode.RGB,
    ColorMode.RGBW,
    ColorMode.RGBWW,
    ColorMode.XY,
    ColorMode.WHITE,
}


class MorningAlarmCoordinator(DataUpdateCoordinator):
    """Manages alarm scheduling and sequences."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.config_entry = entry
        self._scheduled_cancels: dict[str, Any] = {}
        self._alarm_task: asyncio.Task | None = None
        self.alarm_running = False

    async def _async_update_data(self) -> dict[str, Any]:
        return {"alarm_running": self.alarm_running}

    async def async_setup(self) -> None:
        """Schedule alarms after initial load or reload."""
        self.async_reschedule()

    async def async_shutdown(self) -> None:
        """Cancel all scheduled alarms and stop any running sequence."""
        self._cancel_all_scheduled()
        await self._cancel_alarm_task()

    # ------------------------------------------------------------------ #
    # Scheduling                                                           #
    # ------------------------------------------------------------------ #

    @callback
    def async_reschedule(self) -> None:
        """Cancel existing schedules and schedule next alarm for each enabled day."""
        self._cancel_all_scheduled()
        for day in DAYS:
            if self._is_day_enabled(day):
                self._schedule_day(day)

    def _cancel_all_scheduled(self) -> None:
        for cancel in self._scheduled_cancels.values():
            cancel()
        self._scheduled_cancels.clear()

    @callback
    def _schedule_day(self, day: str) -> None:
        target = self._next_alarm_dt(day)
        if target is None:
            return

        _LOGGER.debug("Scheduling %s alarm at %s", DAY_NAMES[day], target)

        @callback
        def _fired(now: datetime) -> None:
            self._scheduled_cancels.pop(day, None)
            self.hass.async_create_task(
                self._trigger_alarm(day), name=f"morning_alarm_trigger_{day}"
            )

        self._scheduled_cancels[day] = async_track_point_in_time(
            self.hass, _fired, target
        )

    def _is_day_enabled(self, day: str) -> bool:
        return bool(
            self.config_entry.options.get(
                day_enabled_key(day), day not in ("sat", "sun")
            )
        )

    def _next_alarm_dt(self, day: str) -> datetime | None:
        """Return the next local datetime when this day's alarm should fire."""
        time_str = self.config_entry.options.get(day_time_key(day), DEFAULT_ALARM_TIME)
        try:
            parts = time_str.split(":")
            h, m = int(parts[0]), int(parts[1])
        except (ValueError, AttributeError, IndexError):
            _LOGGER.error("Invalid alarm time %r for %s", time_str, day)
            return None

        now = dt_util.now()
        days_ahead = (DAY_WEEKDAY[day] - now.weekday()) % 7

        candidate = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if days_ahead == 0 and candidate <= now:
            days_ahead = 7

        return candidate + timedelta(days=days_ahead)

    # ------------------------------------------------------------------ #
    # Trigger / stop                                                       #
    # ------------------------------------------------------------------ #

    async def _trigger_alarm(self, day: str) -> None:
        _LOGGER.info("Morning alarm triggered (%s)", DAY_NAMES[day])
        await self.async_run_alarm()
        if self._is_day_enabled(day):
            self._schedule_day(day)

    async def async_run_alarm(self) -> None:
        """Start the alarm sequence. Called by both scheduler and test button."""
        if self._alarm_task and not self._alarm_task.done():
            _LOGGER.warning("Alarm already running - ignoring duplicate trigger")
            return
        self._alarm_task = self.hass.async_create_task(
            self._alarm_sequence(), name="morning_alarm_sequence"
        )

    async def async_stop_alarm(self) -> None:
        """Cancel a running alarm and pause the media player."""
        await self._cancel_alarm_task()
        self.alarm_running = False
        self.async_set_updated_data({"alarm_running": False})
        await self._pause_media()

    async def _cancel_alarm_task(self) -> None:
        if self._alarm_task and not self._alarm_task.done():
            _LOGGER.debug("Cancelling alarm task")
            self._alarm_task.cancel()
            try:
                await self._alarm_task
            except asyncio.CancelledError:
                pass
        self._alarm_task = None

    # ------------------------------------------------------------------ #
    # Alarm sequence                                                       #
    # ------------------------------------------------------------------ #

    async def _alarm_sequence(self) -> None:
        try:
            self.alarm_running = True
            self.async_set_updated_data({"alarm_running": True})

            # Audio and lighting run concurrently; each handles its own errors.
            await asyncio.gather(
                self._start_media(),
                self._lighting_sequence(),
                self._volume_sequence(),
                return_exceptions=True,
            )
        except asyncio.CancelledError:
            _LOGGER.debug("Alarm sequence cancelled")
            raise
        finally:
            self.alarm_running = False
            self.async_set_updated_data({"alarm_running": False})

    # ------------------------------------------------------------------ #
    # Audio                                                                #
    # ------------------------------------------------------------------ #

    async def _start_media(self) -> None:
        player = self.config_entry.options.get(CONF_MEDIA_PLAYER)
        content_id = self.config_entry.options.get(CONF_MEDIA_CONTENT_ID, "")
        if not player:
            _LOGGER.debug("No media player configured")
            return
        start_vol = int(self.config_entry.options.get(CONF_START_VOLUME, DEFAULT_START_VOLUME))
        try:
            await self.hass.services.async_call(
                "media_player",
                "volume_set",
                {"entity_id": player, "volume_level": round(start_vol / 100, 2)},
                blocking=True,
            )
        except Exception as exc:
            _LOGGER.error("Failed to set initial volume on %s: %s", player, exc)
        try:
            await self.hass.services.async_call(
                "media_player",
                "play_media",
                {
                    "entity_id": player,
                    "media_content_id": content_id,
                    "media_content_type": "channel",
                },
                blocking=True,
            )
            _LOGGER.debug("Media started on %s", player)
        except Exception as exc:
            _LOGGER.error("Failed to start media on %s: %s", player, exc)

    async def _pause_media(self) -> None:
        player = self.config_entry.options.get(CONF_MEDIA_PLAYER)
        if not player:
            return
        try:
            await self.hass.services.async_call(
                "media_player",
                "media_pause",
                {"entity_id": player},
                blocking=True,
            )
        except Exception as exc:
            _LOGGER.error("Failed to pause media on %s: %s", player, exc)

    # ------------------------------------------------------------------ #
    # Volume                                                               #
    # ------------------------------------------------------------------ #

    async def _volume_sequence(self) -> None:
        player = self.config_entry.options.get(CONF_MEDIA_PLAYER)
        if not player:
            return
        opts = self.config_entry.options
        start_vol = int(opts.get(CONF_START_VOLUME, DEFAULT_START_VOLUME))
        final_vol = int(opts.get(CONF_FINAL_VOLUME, DEFAULT_FINAL_VOLUME))
        fade_min = int(opts.get(CONF_FADE_DURATION, DEFAULT_FADE_DURATION))
        num_steps = max(1, (fade_min * 60) // FADE_STEP_INTERVAL)
        step = 0
        try:
            for step in range(1, num_steps + 1):
                await asyncio.sleep(FADE_STEP_INTERVAL)
                current_vol = max(
                    start_vol,
                    min(final_vol, round(start_vol + (final_vol - start_vol) * step / num_steps)),
                )
                await self._set_volume(player, current_vol)
        except asyncio.CancelledError:
            _LOGGER.debug("Volume sequence cancelled at step %d/%d", step, num_steps)
            raise

    async def _set_volume(self, entity_id: str, volume_pct: int) -> None:
        try:
            await self.hass.services.async_call(
                "media_player",
                "volume_set",
                {"entity_id": entity_id, "volume_level": round(volume_pct / 100, 2)},
                blocking=False,
            )
        except Exception as exc:
            _LOGGER.error("Failed to set volume on %s: %s", entity_id, exc)

    # ------------------------------------------------------------------ #
    # Lighting                                                             #
    # ------------------------------------------------------------------ #

    async def _lighting_sequence(self) -> None:
        opts = self.config_entry.options
        start_pct = int(opts.get(CONF_START_BRIGHTNESS, DEFAULT_START_BRIGHTNESS))
        threshold_pct = int(opts.get(CONF_THRESHOLD_BRIGHTNESS, DEFAULT_THRESHOLD_BRIGHTNESS))
        final_pct = int(opts.get(CONF_FINAL_BRIGHTNESS, DEFAULT_FINAL_BRIGHTNESS))
        fade_min = int(opts.get(CONF_FADE_DURATION, DEFAULT_FADE_DURATION))
        dimmable: list[str] = list(opts.get(CONF_DIMMABLE_LIGHTS, []))
        onoff: list[str] = list(opts.get(CONF_ONOFF_LIGHTS, []))

        if not dimmable and not onoff:
            _LOGGER.debug("No lights configured")
            return

        num_steps = max(1, (fade_min * 60) // FADE_STEP_INTERVAL)
        threshold_reached = False
        step = 0

        if dimmable:
            await self._set_brightness(dimmable, start_pct)

        try:
            for step in range(1, num_steps + 1):
                await asyncio.sleep(FADE_STEP_INTERVAL)

                current_pct = max(
                    1, min(100, round(start_pct + (final_pct - start_pct) * step / num_steps))
                )

                if dimmable:
                    await self._set_brightness(dimmable, current_pct)

                if not threshold_reached and current_pct >= threshold_pct:
                    threshold_reached = True
                    _LOGGER.debug(
                        "Threshold %d%% reached - turning on on/off lights", threshold_pct
                    )
                    if onoff:
                        await self._turn_on_lights(onoff)

        except asyncio.CancelledError:
            _LOGGER.debug("Lighting cancelled at step %d/%d", step, num_steps)
            raise

    async def _set_brightness(self, entity_ids: list, brightness_pct: int) -> None:
        brightness_ha = round(brightness_pct / 100 * 255)
        for entity_id in entity_ids:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unavailable", "unknown"):
                _LOGGER.debug("Skipping unavailable light %s", entity_id)
                continue
            supported = set(state.attributes.get("supported_color_modes", []))
            has_brightness = bool(supported & _BRIGHTNESS_COLOR_MODES)
            try:
                data: dict[str, Any] = {"entity_id": entity_id}
                if has_brightness:
                    data["brightness"] = brightness_ha
                await self.hass.services.async_call(
                    "light", "turn_on", data, blocking=False
                )
            except Exception as exc:
                _LOGGER.error("Failed to set brightness on %s: %s", entity_id, exc)

    async def _turn_on_lights(self, entity_ids: list) -> None:
        for entity_id in entity_ids:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unavailable", "unknown"):
                _LOGGER.debug("Skipping unavailable light %s", entity_id)
                continue
            try:
                await self.hass.services.async_call(
                    "light", "turn_on", {"entity_id": entity_id}, blocking=False
                )
            except Exception as exc:
                _LOGGER.error("Failed to turn on %s: %s", entity_id, exc)
