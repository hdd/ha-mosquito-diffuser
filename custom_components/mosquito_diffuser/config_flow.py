"""Config and options flow for the Mosquito Diffuser integration."""

from __future__ import annotations

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
    TextSelector,
    TimeSelector,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_LIFE_HOURS,
    CONF_LOW_THRESHOLD,
    CONF_NAME,
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
    OUTLET_DOMAINS,
)


def _base_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Schema for identity/outlet/cartridge fields (user + options flows)."""
    fields: dict[vol.Marker, Any] = {
        vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): TextSelector(),
        vol.Required(
            CONF_LIFE_HOURS,
            default=defaults.get(CONF_LIFE_HOURS, DEFAULT_LIFE_HOURS),
        ): NumberSelector(
            NumberSelectorConfig(
                min=1, max=2000, step=1, unit_of_measurement="h", mode=NumberSelectorMode.BOX
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
    }
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


class MosquitoDiffuserConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Stash input between the two steps."""
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Step 1: name, outlet and cartridge settings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_OUTLET])
            self._abort_if_unique_id_configured()
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

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        current: dict[str, Any] = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
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
                return self.async_create_entry(title="", data=user_input)

        fields = dict(_base_schema(current).schema)
        fields.update(_times_schema(current).schema)
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(fields), errors=errors
        )
