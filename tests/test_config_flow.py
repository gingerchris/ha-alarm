"""Tests for Morning Alarm config flow."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.morning_alarm.const import DOMAIN


@pytest.fixture(autouse=True)
def bypass_setup():
    """Prevent actual integration setup during config flow tests."""
    with patch(
        "custom_components.morning_alarm.async_setup_entry",
        return_value=True,
    ):
        yield


async def test_config_flow_full(hass: HomeAssistant) -> None:
    """Test the complete multi-step config flow creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"title": "My Alarm"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "audio"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "media_player_entity": "media_player.yoto",
            "media_content_id": "yoto://station",
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "lights"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "dimmable_lights": ["light.bedroom"],
            "onoff_lights": [],
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "brightness"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "fade_duration": 10,
            "start_brightness": 1,
            "threshold_brightness": 40,
            "final_brightness": 100,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "schedule"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "mon_enabled": True,
            "mon_time": "07:00",
            "tue_enabled": True,
            "tue_time": "07:30",
            "wed_enabled": True,
            "wed_time": "07:00",
            "thu_enabled": True,
            "thu_time": "07:30",
            "fri_enabled": True,
            "fri_time": "07:00",
            "sat_enabled": False,
            "sat_time": "08:00",
            "sun_enabled": False,
            "sun_time": "08:00",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Alarm"
    assert result["options"]["media_player_entity"] == "media_player.yoto"
    assert result["options"]["mon_enabled"] is True
    assert result["options"]["mon_time"] == "07:00"
    assert result["options"]["sat_enabled"] is False


async def test_config_flow_normalises_time(hass: HomeAssistant) -> None:
    """Times with seconds (HH:MM:SS from TimeSelector) are stored as HH:MM."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"title": "Test"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"dimmable_lights": [], "onoff_lights": []}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"fade_duration": 10, "start_brightness": 1, "threshold_brightness": 40, "final_brightness": 100},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "mon_enabled": True, "mon_time": "07:00:00",
            "tue_enabled": False, "tue_time": "07:30:00",
            "wed_enabled": False, "wed_time": "07:00:00",
            "thu_enabled": False, "thu_time": "07:30:00",
            "fri_enabled": False, "fri_time": "07:00:00",
            "sat_enabled": False, "sat_time": "08:00:00",
            "sun_enabled": False, "sun_time": "08:00:00",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["options"]["mon_time"] == "07:00"


async def test_options_flow(hass: HomeAssistant, mock_config_entry) -> None:
    """Options flow updates existing options."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "audio"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"media_player_entity": "media_player.new", "media_content_id": "new://station"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "lights"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"dimmable_lights": [], "onoff_lights": []},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"fade_duration": 15, "start_brightness": 2, "threshold_brightness": 50, "final_brightness": 90},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "mon_enabled": False, "mon_time": "08:00",
            "tue_enabled": False, "tue_time": "08:00",
            "wed_enabled": False, "wed_time": "08:00",
            "thu_enabled": False, "thu_time": "08:00",
            "fri_enabled": False, "fri_time": "08:00",
            "sat_enabled": False, "sat_time": "09:00",
            "sun_enabled": False, "sun_time": "09:00",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["media_player_entity"] == "media_player.new"
    assert result["data"]["fade_duration"] == 15
    assert result["data"]["mon_enabled"] is False
