"""Test fixtures for Morning Alarm."""
from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.morning_alarm.const import DOMAIN

DEFAULT_OPTIONS = {
    "media_player_entity": "media_player.test_yoto",
    "media_content_id": "yoto://test-station",
    "dimmable_lights": ["light.bedroom_dimmable"],
    "onoff_lights": ["light.bedroom_lamp"],
    "start_brightness": 1,
    "threshold_brightness": 40,
    "final_brightness": 100,
    "fade_duration": 1,
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
}


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Morning Alarm",
        data={},
        options=DEFAULT_OPTIONS,
        entry_id="test_entry_id_1234",
    )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield
