"""Config and options flow for the Mosquito Diffuser integration."""

from __future__ import annotations

import traceback

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TimeSelector,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_LEVEL_PCT,
    CONF_LIFE_HOURS,
    CONF_LIFE_PRESET,
    CONF_LOW_THRESHOLD,
    CONF_NAME,
    CONF_NEW_CARTRIDGE,
    CONF_OFF_TIME,
    CONF_ON_TIME,
    CONF_OUTLET,
    CONF_SCHEDULE_ENABLED,
    DEFAULT_LIFE_HOURS,
    DEFAULT_LOW_THRESHOLD,
    DEFAULT_NAME,
    DEFAULT_OFF_TIME,
    DEFAULT_ON_TIME,
    DOMAIN,
    LIFE_PRESETS,
    OUTLET_DOMAINS,
)


def _preset_options() -> list[dict[str, str]]:
    """Preset dropdown entries."""
    return [
        {"value": "preset_15d", "label": "15 days (360 h active)"},
        {"value": "preset_1m", "label": "1 month (720 h active)"},
        {"value": "preset_3m", "label": "3 months (2,160 h active)"},
        {"value": "custom", "label": "Custom hours"},
    ]


def _base_schema(defaults: dict[str, Any], include_level: bool = False) -> vol.Schema:
    """Schema for identity/outlet/cartridge fields (user + options flows)."""
    current_life = float(defaults.get(CONF_LIFE_HOURS, DEFAULT_LIFE_HOURS) or DEFAULT_LIFE_HOURS)
    current_preset = next(
        (key for key, hours in LIFE_PRESETS.items() if hours == current_life), "custom"
    )
    fields: dict[vol.Marker, Any] = {
        vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): TextSelector(),
    }
    if include_level:
        fields[vol.Required(
            CONF_LEVEL_PCT,
            default=defaults.get(CONF_LEVEL_PCT, 100),
        )] = NumberSelector(
            NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%")
        )
    fields.update({
        vol.Required(
            CONF_LIFE_PRESET,
            default=defaults.get(CONF_LIFE_PRESET, current_preset),
        ): SelectSelector(
            SelectSelectorConfig(options=_preset_options(), mode=SelectSelectorMode.DROPDOWN)
        ),
        vol.Required(
            CONF_LIFE_HOURS,
            default=current_life,
            description="Used when preset is 'Custom hours'",
        ): NumberSelector(
            NumberSelectorConfig(
                min=1,
                max=8760,
                step=1,
                unit_of_measurement="h",
                mode=NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_CUSTOM_DAYS,
            default=defaults.get(CONF_CUSTOM_DAYS, 0),
        ): NumberSelector(
            NumberSelectorConfig(min=0, max=365, step=1, mode=NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_CUSTOM_HPD,
            default=defaults.get(CONF_CUSTOM_HPD, 24),
        ): NumberSelector(
            NumberSelectorConfig(
                min=0.5, max=24, step=0.5, unit_of_measurement="h/day"
            )
        ),
        vol.Required(
            CONF_LOW_THRESHOLD,
            default=defaults.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD),
        ): NumberSelector(
            NumberSelectorConfig(min=1, max=90, step=1, unit_of_measurement="%")
        ),
        vol.Required(
            CONF_SCHEDULE_ENABLED,
            default=defaults.get(CONF_SCHEDULE_ENABLED, True),
        ): BooleanSelector(),
    })
    if CONF_OUTLET in defaults:
        fields[vol.Required(CONF_OUTLET, default=defaults[CONF_OUTLET])] = EntitySelector(
            EntitySelectorConfig(domain=OUTLET_DOMAINS)
        )
    else:
        fields[vol.Required(CONF_OUTLET)] = EntitySelector(
            EntitySelectorConfig(domain=OUTLET_DOMAINS)
        )
    return vol.Schema(fields)


def _times_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_ON_TIME, default=defaults.get(CONF_ON_TIME, DEFAULT_ON_TIME)
            ): TimeSelector(),
            vol.Optional(
                CONF_OFF_TIME, default=defaults.get(CONF_OFF_TIME, DEFAULT_OFF_TIME)
            ): TimeSelector(),
        }
    )


def _apply_life_preset(user_input: dict[str, Any]) -> None:
    """Resolve the preset dropdown / days+hours fields into total life hours."""
    preset = user_input.get(CONF_LIFE_PRESET, "custom")
    hours = LIFE_PRESETS.get(preset)
    if hours is not None:
        user_input[CONF_LIFE_HOURS] = hours
        return
    # Custom: days × hours-per-day wins over a plain hour count when set.
    days = float(user_input.get(CONF_CUSTOM_DAYS, 0) or 0)
    if days > 0:
        hpd = float(user_input.get(CONF_CUSTOM_HPD, 24) or 24)
        user_input[CONF_LIFE_HOURS] = round(days * hpd, 2)


class MosquitoDiffuserConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Stash input between the two steps."""
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Step 1: name, outlet and cartridge settings."""
        try:
            return await self._async_user_step(user_input)
        except Exception:
            return self._debug_form("user", traceback.format_exc()[-1200:])

    def _debug_form(self, step_id: str, tb: str):
        """DEBUG build: surface the crash back through the flow response."""
        schema = vol.Schema(
            {vol.Required("debug_traceback", default=tb): TextSelector()}
        )
        return self.async_show_form(step_id=step_id, data_schema=schema)

    async def _async_user_step(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_OUTLET])
            self._abort_if_unique_id_configured()
            _apply_life_preset(user_input)
            self._data = dict(user_input)
            if user_input[CONF_SCHEDULE_ENABLED]:
                return await self.async_step_schedule()
            return self._async_finish()
        return self.async_show_form(step_id="user", data_schema=_base_schema({}), errors=errors)

    async def async_step_schedule(self, user_input: dict[str, Any] | None = None):
        """Step 2: on/off times."""
        errors: dict[str, str] = {}
        if user_input is not None:
            on_time = dt_util.parse_time(str(user_input.get(CONF_ON_TIME) or ""))
            off_time = dt_util.parse_time(str(user_input.get(CONF_OFF_TIME) or ""))
            if not on_time or not off_time:
                errors["base"] = "invalid_time"
            else:
                self._data.update(user_input)
                return self._async_finish()
        return self.async_show_form(
            step_id="schedule", data_schema=_times_schema({}), errors=errors
        )

    @callback
    def _async_finish(self):
        return self.async_create_entry(
            title=str(self._data.get(CONF_NAME, DEFAULT_NAME)), data=self._data
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MosquitoDiffuserOptionsFlow()


class MosquitoDiffuserOptionsFlow(config_entries.OptionsFlow):
    """Edit every setting of an existing instance in one form."""

    def _coordinator(self):
        """Return the coordinator, or None if not reachable from this flow.

        Access to hass/config_entry varies across HA versions; this must
        never raise, or the whole options dialog 500s.
        """
        try:
            hass = getattr(self, "hass", None)
            entry = getattr(self, "config_entry", None)
            if hass is None or entry is None:
                return None
            return hass.data.get(DOMAIN, {}).get(entry.entry_id)
        except Exception:  # noqa: BLE001 - dialog must always render
            return None

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        try:
            return await self._async_init_step(user_input)
        except Exception:
            return self._debug_form("init", traceback.format_exc()[-1200:])

    async def _async_init_step(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        current: dict[str, Any] = {**self.config_entry.data, **self.config_entry.options}
        coordinator = self._coordinator()

        if user_input is not None:
            _apply_life_preset(user_input)
            # Calibration: not persisted in options, applied to the counter
            level = user_input.pop(CONF_LEVEL_PCT, None)
            new_cartridge = bool(user_input.pop(CONF_NEW_CARTRIDGE, False))
            enabled = bool(user_input.get(CONF_SCHEDULE_ENABLED, False))
            on_time = dt_util.parse_time(str(user_input.get(CONF_ON_TIME) or ""))
            off_time = dt_util.parse_time(str(user_input.get(CONF_OFF_TIME) or ""))
            if enabled and (not on_time or not off_time):
                errors["base"] = "times_required"
            else:
                if on_time:
                    user_input[CONF_ON_TIME] = on_time.strftime("%H:%M")
                if off_time:
                    user_input[CONF_OFF_TIME] = off_time.strftime("%H:%M")
                if coordinator is not None:
                    if new_cartridge:
                        await coordinator.async_reset_cartridge()
                    elif level is not None and abs(float(level) - coordinator.remaining_pct) >= 0.5:
                        await coordinator.async_set_level(float(level))
                return self.async_create_entry(title="", data=user_input)

        include_level = coordinator is not None
        if include_level:
            current[CONF_LEVEL_PCT] = round(coordinator.remaining_pct, 0)
        fields = dict(_base_schema(current, include_level=include_level).schema)
        fields.update(_times_schema(current).schema)
        if coordinator is not None:
            fields[vol.Required(CONF_NEW_CARTRIDGE, default=False)] = BooleanSelector()
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(fields), errors=errors
        )
