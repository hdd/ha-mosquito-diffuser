"""Reset button for the Mosquito Diffuser integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from .coordinator import MosquitoDiffuserCoordinator
from .entity import MosquitoDiffuserEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up the reset button."""
    coordinator: MosquitoDiffuserCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NewCartridgeButton(coordinator)])


class NewCartridgeButton(MosquitoDiffuserEntity, ButtonEntity):
    """Press when a fresh cartridge is installed."""

    _attr_name = "New cartridge"
    _attr_icon = "mdi:restart"

    def __init__(self, coordinator: MosquitoDiffuserCoordinator) -> None:
        super().__init__(coordinator, "new_cartridge")

    async def async_press(self) -> None:
        """Zero the counter and re-stamp the install time."""
        await self.coordinator.async_reset_cartridge()
