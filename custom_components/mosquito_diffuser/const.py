"""Constants for the Mosquito Diffuser integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "mosquito_diffuser"

PLATFORMS = [Platform.BUTTON, Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]

CONF_NAME = "name"
CONF_OUTLET = "outlet_entity"
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

OUTLET_DOMAINS = ["switch", "light", "fan", "humidifier"]

STORAGE_VERSION = 1
PERSIST_DELAY = 60  # seconds after a change before the accumulator is flushed
TICK_INTERVAL = timedelta(seconds=60)
