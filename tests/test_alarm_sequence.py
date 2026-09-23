"""Tests for alarm sequence: lighting fade, audio, cancellation."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.morning_alarm.const import DOMAIN
from custom_components.morning_alarm.coordinator import MorningAlarmCoordinator


def _make_coordinator(hass: HomeAssistant, mock_config_entry) -> MorningAlarmCoordinator:
    mock_config_entry.add_to_hass(hass)
    return MorningAlarmCoordinator(hass, mock_config_entry)


# ------------------------------------------------------------------ #
# Audio                                                                #
# ------------------------------------------------------------------ #

async def test_start_media_calls_play(hass: HomeAssistant, mock_config_entry) -> None:
    """_start_media calls media_player.play_media service."""
    coordinator = _make_coordinator(hass, mock_config_entry)
    calls = async_mock_service(hass, "media_player", "play_media")

    await coordinator._start_media()

    assert len(calls) == 1
    assert calls[0].data["entity_id"] == "media_player.test_yoto"
    assert calls[0].data["media_content_id"] == "yoto://test-station"


async def test_start_media_skipped_when_no_player(hass: HomeAssistant, mock_config_entry) -> None:
    """_start_media is a no-op when no media player is configured."""
    mock_config_entry.add_to_hass(hass)
    opts = dict(mock_config_entry.options)
    opts["media_player_entity"] = ""
    hass.config_entries.async_update_entry(mock_config_entry, options=opts)
    coordinator = MorningAlarmCoordinator(hass, mock_config_entry)

    calls = async_mock_service(hass, "media_player", "play_media")
    await coordinator._start_media()
    assert len(calls) == 0


async def test_start_media_continues_on_error(hass: HomeAssistant, mock_config_entry) -> None:
    """Media player error does not propagate (lighting still runs)."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    with patch(
        "homeassistant.core.ServiceRegistry.async_call",
        side_effect=Exception("unavailable"),
    ):
        await coordinator._start_media()  # should not raise


# ------------------------------------------------------------------ #
# Lighting: brightness calculations                                    #
# ------------------------------------------------------------------ #

async def test_lighting_sets_initial_brightness(hass: HomeAssistant, mock_config_entry) -> None:
    """Dimmable lights are set to start_brightness before the fade begins."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    hass.states.async_set(
        "light.bedroom_dimmable",
        "on",
        {"supported_color_modes": ["brightness"]},
    )

    calls = async_mock_service(hass, "light", "turn_on")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await coordinator._lighting_sequence()

    brightness_calls = [c for c in calls if "brightness" in c.data]
    assert len(brightness_calls) > 0
    # First call brightness should be start_brightness (1% → round(1/100*255) = 3)
    assert brightness_calls[0].data["brightness"] == round(1 / 100 * 255)


async def test_lighting_brightness_increases(hass: HomeAssistant, mock_config_entry) -> None:
    """Brightness values are non-decreasing across all steps."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    hass.states.async_set(
        "light.bedroom_dimmable",
        "on",
        {"supported_color_modes": ["brightness"]},
    )

    calls = async_mock_service(hass, "light", "turn_on")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await coordinator._lighting_sequence()

    brightness_values = [c.data["brightness"] for c in calls if "brightness" in c.data]
    assert len(brightness_values) > 1
    for i in range(1, len(brightness_values)):
        assert brightness_values[i] >= brightness_values[i - 1]


async def test_lighting_reaches_final_brightness(hass: HomeAssistant, mock_config_entry) -> None:
    """The last brightness call equals final_brightness (100% → 255)."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    hass.states.async_set(
        "light.bedroom_dimmable",
        "on",
        {"supported_color_modes": ["brightness"]},
    )

    calls = async_mock_service(hass, "light", "turn_on")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await coordinator._lighting_sequence()

    brightness_values = [c.data["brightness"] for c in calls if "brightness" in c.data]
    assert brightness_values[-1] == 255  # 100%


# ------------------------------------------------------------------ #
# Lighting: threshold                                                  #
# ------------------------------------------------------------------ #

async def test_onoff_lights_turn_on_at_threshold(hass: HomeAssistant, mock_config_entry) -> None:
    """On/off lights are turned on exactly once when brightness crosses threshold."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    hass.states.async_set(
        "light.bedroom_dimmable", "on", {"supported_color_modes": ["brightness"]}
    )
    hass.states.async_set(
        "light.bedroom_lamp", "off", {"supported_color_modes": ["onoff"]}
    )

    calls = async_mock_service(hass, "light", "turn_on")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await coordinator._lighting_sequence()

    lamp_calls = [c for c in calls if c.data.get("entity_id") == "light.bedroom_lamp"]
    assert len(lamp_calls) == 1


# ------------------------------------------------------------------ #
# Lighting: unavailable / non-dimmable lights                         #
# ------------------------------------------------------------------ #

async def test_unavailable_light_skipped(hass: HomeAssistant, mock_config_entry) -> None:
    """Unavailable lights receive no service calls."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    hass.states.async_set(
        "light.bedroom_dimmable", "unavailable", {"supported_color_modes": ["brightness"]}
    )

    calls = async_mock_service(hass, "light", "turn_on")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await coordinator._lighting_sequence()

    dimmable_calls = [c for c in calls if c.data.get("entity_id") == "light.bedroom_dimmable"]
    assert len(dimmable_calls) == 0


async def test_non_dimmable_light_turned_on_without_brightness(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """A light in dimmable_lights with only on/off support gets turn_on without brightness."""
    mock_config_entry.add_to_hass(hass)
    opts = dict(mock_config_entry.options)
    opts["dimmable_lights"] = ["light.onoff_only"]
    opts["onoff_lights"] = []
    hass.config_entries.async_update_entry(mock_config_entry, options=opts)
    coordinator = MorningAlarmCoordinator(hass, mock_config_entry)

    hass.states.async_set(
        "light.onoff_only", "off", {"supported_color_modes": ["onoff"]}
    )

    calls = async_mock_service(hass, "light", "turn_on")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await coordinator._lighting_sequence()

    brightness_calls = [c for c in calls if "brightness" in c.data]
    plain_calls = [c for c in calls if "brightness" not in c.data]
    assert len(brightness_calls) == 0
    assert len(plain_calls) > 0


# ------------------------------------------------------------------ #
# Cancellation                                                         #
# ------------------------------------------------------------------ #

async def test_stop_alarm_cancels_task(hass: HomeAssistant, mock_config_entry) -> None:
    """async_stop_alarm cancels the running alarm task."""
    coordinator = _make_coordinator(hass, mock_config_entry)
    async_mock_service(hass, "media_player", "media_pause")

    async def slow_sequence():
        coordinator.alarm_running = True
        await asyncio.sleep(3600)

    coordinator._alarm_task = hass.async_create_task(slow_sequence())
    await asyncio.sleep(0)  # Let the task start

    await coordinator.async_stop_alarm()

    assert coordinator._alarm_task is None
    assert not coordinator.alarm_running


async def test_lighting_cancelled_re_raises(hass: HomeAssistant, mock_config_entry) -> None:
    """_lighting_sequence re-raises CancelledError so the task is properly cancelled."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    hass.states.async_set(
        "light.bedroom_dimmable", "on", {"supported_color_modes": ["brightness"]}
    )

    async_mock_service(hass, "light", "turn_on")

    call_count = 0

    async def cancel_on_second(n):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError

    with patch("asyncio.sleep", side_effect=cancel_on_second):
        with pytest.raises(asyncio.CancelledError):
            await coordinator._lighting_sequence()


# ------------------------------------------------------------------ #
# Full alarm sequence                                                  #
# ------------------------------------------------------------------ #

async def test_alarm_sequence_sets_running_flag(hass: HomeAssistant, mock_config_entry) -> None:
    """alarm_running is True during sequence and False after."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    hass.states.async_set(
        "light.bedroom_dimmable", "on", {"supported_color_modes": ["brightness"]}
    )
    hass.states.async_set("light.bedroom_lamp", "off", {"supported_color_modes": ["onoff"]})

    async_mock_service(hass, "media_player", "play_media")
    async_mock_service(hass, "light", "turn_on")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await coordinator._alarm_sequence()

    assert not coordinator.alarm_running


async def test_yoto_failure_does_not_stop_lighting(hass: HomeAssistant, mock_config_entry) -> None:
    """If media player fails, the lighting sequence still completes."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    hass.states.async_set(
        "light.bedroom_dimmable", "on", {"supported_color_modes": ["brightness"]}
    )

    light_calls = async_mock_service(hass, "light", "turn_on")
    async_mock_service(hass, "media_player", "play_media")

    async def failing_media():
        raise Exception("Yoto down")

    with (
        patch.object(coordinator, "_start_media", side_effect=failing_media),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        await coordinator._alarm_sequence()

    assert len(light_calls) > 0
