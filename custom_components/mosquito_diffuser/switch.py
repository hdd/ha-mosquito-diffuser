"""Schedule switch for the Mosquito Diffuser integration."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory

from .const import DOMAIN
from .coordinator import MosquitoDiffuserCoordinator
from .entity import MosquitoDiffuserEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up the schedule switch (only when a schedule is configured)."""
    coordinator: MosquitoDiffuserCoordinator = hass.data[DOMAIN][entry.entry_id]
    if coordinator.schedule_enabled:
        async_add_entities([ScheduleSwitch(coordinator)])


class ScheduleSwitch(MosquitoDiffuserEntity, SwitchEntity):
    """Pause/resume the built-in on/off schedule without deleting it."""

    _attr_name = "Schedule"
    _attr_icon = "mdi:calendar-clock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: MosquitoDiffuserCoordinator) -> None:
        super().__init__(coordinator, "schedule")

    @property
    def is_on(self) -> bool:
        return self.coordinator.schedule_active

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_schedule_active(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_schedule_active(False)
