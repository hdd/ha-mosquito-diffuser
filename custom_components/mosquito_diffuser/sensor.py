"""Sensors for the Mosquito Diffuser integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import MosquitoDiffuserCoordinator
from .entity import MosquitoDiffuserEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up Mosquito Diffuser sensors."""
    coordinator: MosquitoDiffuserCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            UsedSensor(coordinator),
            RemainingSensor(coordinator),
            RemainingPercentSensor(coordinator),
            DaysLeftSensor(coordinator),
            EstimatedEmptySensor(coordinator),
        ]
    )


class MosquitoSensorBase(MosquitoDiffuserEntity, SensorEntity):
    """Common constructor bits for our sensors."""

    def __init__(
        self,
        coordinator: MosquitoDiffuserCoordinator,
        key: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, key)
        self._attr_name = name
        self._attr_icon = icon


class UsedSensor(MosquitoSensorBase):
    """Hours of active diffuser time for the current cartridge."""

    def __init__(self, coordinator: MosquitoDiffuserCoordinator) -> None:
        super().__init__(coordinator, "used", "Used", "mdi:clock-outline")
        self._attr_native_unit_of_measurement = "h"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> float:
        return round(self.coordinator.used_hours, 1)


class RemainingSensor(MosquitoSensorBase):
    """Rated hours left in the current cartridge."""

    def __init__(self, coordinator: MosquitoDiffuserCoordinator) -> None:
        super().__init__(coordinator, "remaining", "Remaining runtime", "mdi:clock-outline")
        self._attr_native_unit_of_measurement = "h"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float:
        return round(self.coordinator.remaining_hours, 1)


class RemainingPercentSensor(MosquitoSensorBase):
    """Remaining cartridge life as a percentage."""

    def __init__(self, coordinator: MosquitoDiffuserCoordinator) -> None:
        super().__init__(coordinator, "remaining_pct", "Remaining", "mdi:gauge")
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float:
        return round(self.coordinator.remaining_pct, 0)


class DaysLeftSensor(MosquitoSensorBase):
    """Days until the cartridge is empty at the measured usage pace."""

    def __init__(self, coordinator: MosquitoDiffuserCoordinator) -> None:
        super().__init__(coordinator, "days_left", "Days left", "mdi:calendar-clock")
        self._attr_native_unit_of_measurement = "d"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float:
        return self.coordinator.days_left

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "average_hours_per_day": round(self.coordinator.avg_hours_per_day, 1),
            "installed_at": dt_util.as_local(self.coordinator.installed_at).isoformat(),
            "rated_life_hours": self.coordinator.life_hours,
            "outlet_entity": self.coordinator.outlet_entity,
        }


class EstimatedEmptySensor(MosquitoSensorBase):
    """Timestamp when the cartridge is expected to run out."""

    def __init__(self, coordinator: MosquitoDiffuserCoordinator) -> None:
        super().__init__(coordinator, "estimated_empty", "Estimated empty", "mdi:calendar-remove")
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self):
        return dt_util.utcnow() + timedelta(days=self.coordinator.days_left)
