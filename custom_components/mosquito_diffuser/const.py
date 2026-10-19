"""Constants for the Mosquito Diffuser integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "mosquito_diffuser"

PLATFORMS = [
    Platform.BUTTON,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONF_NAME = "name"
CONF_OUTLET = "outlet_entity"
CONF_LIFE_PRESET = "life_preset"
CONF_LEVEL_PCT = "level_pct"
CONF_NEW_CARTRIDGE = "mark_new_cartridge"
CONF_CUSTOM_DAYS = "custom_days"
CONF_CUSTOM_HPD = "custom_hours_per_day"
CONF_LIFE_HOURS = "life_hours"
CONF_LOW_THRESHOLD = "low_threshold_pct"
CONF_SCHEDULE_ENABLED = "schedule_enabled"
CONF_ON_TIME = "on_time"
CONF_OFF_TIME = "off_time"

DEFAULT_NAME = "Mosquito Diffuser"
DEFAULT_LIFE_HOURS = 360.0  # ~45 nights x 8 h, typical for liquid refills
DEFAULT_LOW_THRESHOLD = 15
DEFAULT_ON_TIME = "22:00"
DEFAULT_OFF_TIME = "08:00"
MAX_LIFE_HOURS = 8760  # one year of continuous use

# Presets map to total ACTIVE hours (hours only accrue while the outlet is on)
LIFE_PRESETS: dict[str, float | None] = {
    "preset_15d": 360.0,  # 15 days of continuous use
    "preset_1m": 720.0,  # 1 month of continuous use
    "preset_3m": 2160.0,  # 3 months of continuous use
    "custom": None,
}

OUTLET_DOMAINS = ["switch", "light", "fan", "humidifier"]

STORAGE_VERSION = 1
PERSIST_DELAY = 60  # seconds after a change before the accumulator is flushed
TICK_INTERVAL = timedelta(seconds=60)
