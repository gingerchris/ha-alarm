"""Tests for MorningAlarmCoordinator scheduling logic."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.morning_alarm.const import DOMAIN
from custom_components.morning_alarm.coordinator import MorningAlarmCoordinator


def _make_coordinator(hass: HomeAssistant, mock_config_entry) -> MorningAlarmCoordinator:
    mock_config_entry.add_to_hass(hass)
    return MorningAlarmCoordinator(hass, mock_config_entry)


# ------------------------------------------------------------------ #
# _next_alarm_dt                                                       #
# ------------------------------------------------------------------ #

async def test_next_alarm_dt_future_day(hass: HomeAssistant, mock_config_entry) -> None:
    """If the weekday hasn't occurred yet this week, alarm is in the future."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    # Monday 2024-01-08 at 07:00 local time. Freeze at Sunday 2024-01-07 12:00.
    with patch(
        "custom_components.morning_alarm.coordinator.dt_util.now",
        return_value=datetime(2024, 1, 7, 12, 0, 0, tzinfo=timezone.utc),
    ):
        result = coordinator._next_alarm_dt("mon")

    assert result is not None
    assert result.weekday() == 0  # Monday
    assert result.hour == 7
    assert result.minute == 0


async def test_next_alarm_dt_same_day_future(hass: HomeAssistant, mock_config_entry) -> None:
    """Same weekday but alarm time is still in the future → today."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    # Monday 2024-01-08 at 06:00; alarm is 07:00 → today.
    with patch(
        "custom_components.morning_alarm.coordinator.dt_util.now",
        return_value=datetime(2024, 1, 8, 6, 0, 0, tzinfo=timezone.utc),
    ):
        result = coordinator._next_alarm_dt("mon")

    assert result is not None
    assert result.weekday() == 0
    assert result.hour == 7


async def test_next_alarm_dt_same_day_past(hass: HomeAssistant, mock_config_entry) -> None:
    """Same weekday but alarm time has already passed → next week."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    # Monday 2024-01-08 at 08:00; alarm was at 07:00 → next Monday.
    with patch(
        "custom_components.morning_alarm.coordinator.dt_util.now",
        return_value=datetime(2024, 1, 8, 8, 0, 0, tzinfo=timezone.utc),
    ):
        result = coordinator._next_alarm_dt("mon")

    assert result is not None
    assert result.weekday() == 0
    # Should be 7 days later
    assert (result - datetime(2024, 1, 8, 8, 0, 0, tzinfo=timezone.utc)).days == 6


async def test_next_alarm_dt_invalid_time(hass: HomeAssistant, mock_config_entry) -> None:
    """Invalid time string returns None and logs an error."""
    coordinator = _make_coordinator(hass, mock_config_entry)
    opts = dict(mock_config_entry.options)
    opts["mon_time"] = "not-a-time"
    hass.config_entries.async_update_entry(mock_config_entry, options=opts)

    result = coordinator._next_alarm_dt("mon")
    assert result is None


# ------------------------------------------------------------------ #
# _is_day_enabled                                                      #
# ------------------------------------------------------------------ #

async def test_disabled_day_not_scheduled(hass: HomeAssistant, mock_config_entry) -> None:
    """Saturday and Sunday are disabled by default and not scheduled."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    with patch.object(coordinator, "_schedule_day") as mock_schedule:
        coordinator.async_reschedule()
        scheduled_days = [call.args[0] for call in mock_schedule.call_args_list]

    assert "sat" not in scheduled_days
    assert "sun" not in scheduled_days


async def test_enabled_days_are_scheduled(hass: HomeAssistant, mock_config_entry) -> None:
    """Mon-Fri are enabled and should all be scheduled."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    with patch.object(coordinator, "_schedule_day") as mock_schedule:
        coordinator.async_reschedule()
        scheduled_days = [call.args[0] for call in mock_schedule.call_args_list]

    for day in ("mon", "tue", "wed", "thu", "fri"):
        assert day in scheduled_days


# ------------------------------------------------------------------ #
# Schedule changes                                                     #
# ------------------------------------------------------------------ #

async def test_reschedule_cancels_existing(hass: HomeAssistant, mock_config_entry) -> None:
    """Rescheduling cancels all previously scheduled alarms."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    cancel_mock = MagicMock()
    coordinator._scheduled_cancels["mon"] = cancel_mock

    with patch.object(coordinator, "_schedule_day"):
        coordinator.async_reschedule()

    cancel_mock.assert_called_once()
    assert "mon" not in coordinator._scheduled_cancels


async def test_reschedule_no_duplicates(hass: HomeAssistant, mock_config_entry) -> None:
    """Calling reschedule twice doesn't create duplicate scheduled alarms."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    with patch.object(coordinator, "_schedule_day") as mock_schedule:
        coordinator.async_reschedule()
        first_count = mock_schedule.call_count
        coordinator.async_reschedule()
        second_count = mock_schedule.call_count

    assert second_count == first_count * 2


# ------------------------------------------------------------------ #
# Reload / restart survival                                            #
# ------------------------------------------------------------------ #

async def test_setup_schedules_alarms(hass: HomeAssistant, mock_config_entry) -> None:
    """async_setup calls reschedule so alarms are armed after load."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    with patch.object(coordinator, "async_reschedule") as mock_reschedule:
        await coordinator.async_setup()
        mock_reschedule.assert_called_once()


async def test_shutdown_cancels_all(hass: HomeAssistant, mock_config_entry) -> None:
    """async_shutdown cancels schedules and any running alarm task."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    cancel_mock = MagicMock()
    coordinator._scheduled_cancels["mon"] = cancel_mock

    await coordinator.async_shutdown()

    cancel_mock.assert_called_once()
    assert len(coordinator._scheduled_cancels) == 0


# ------------------------------------------------------------------ #
# Duplicate trigger prevention                                         #
# ------------------------------------------------------------------ #

async def test_duplicate_alarm_ignored(hass: HomeAssistant, mock_config_entry) -> None:
    """Second async_run_alarm while alarm is running is a no-op."""
    coordinator = _make_coordinator(hass, mock_config_entry)

    running_task = MagicMock()
    running_task.done.return_value = False
    coordinator._alarm_task = running_task

    with patch.object(coordinator, "_alarm_sequence") as mock_seq:
        await coordinator.async_run_alarm()
        mock_seq.assert_not_called()
