"""Constants for Morning Alarm."""
from __future__ import annotations

DOMAIN = "morning_alarm"

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_NAMES: dict[str, str] = {
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "sun": "Sunday",
}
DAY_WEEKDAY: dict[str, int] = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

CONF_MEDIA_PLAYER = "media_player_entity"
CONF_MEDIA_CONTENT_ID = "media_content_id"
CONF_DIMMABLE_LIGHTS = "dimmable_lights"
CONF_ONOFF_LIGHTS = "onoff_lights"
CONF_START_BRIGHTNESS = "start_brightness"
CONF_THRESHOLD_BRIGHTNESS = "threshold_brightness"
CONF_FINAL_BRIGHTNESS = "final_brightness"
CONF_FADE_DURATION = "fade_duration"

DEFAULT_FADE_DURATION = 10
DEFAULT_START_BRIGHTNESS = 1
DEFAULT_THRESHOLD_BRIGHTNESS = 40
DEFAULT_FINAL_BRIGHTNESS = 100
DEFAULT_ALARM_TIME = "07:00"
DEFAULT_SAT_TIME = "08:00"
DEFAULT_SUN_TIME = "08:00"

FADE_STEP_INTERVAL = 10  # seconds between brightness steps

PLATFORMS = ["binary_sensor", "button", "number", "switch", "time"]


def day_enabled_key(day: str) -> str:
    return f"{day}_enabled"


def day_time_key(day: str) -> str:
    return f"{day}_time"
