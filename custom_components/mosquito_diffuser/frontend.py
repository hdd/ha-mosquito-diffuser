"""Lovelace frontend assets for the Mosquito Diffuser integration.

The companion dashboard card ships inside the integration folder and is
served by Home Assistant itself, so installing the integration is all it
takes: the card is then available at ``/mosquito_diffuser/
mosquito-diffuser-card.js`` and can be added to the Lovelace resources.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "mosquito-diffuser-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILENAME}"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the companion dashboard card from the integration folder."""

    card_path = Path(__file__).parent / "frontend" / CARD_FILENAME

    if hass.http is None:
        _LOGGER.warning("HTTP server not available: dashboard card not served")
        return

    from homeassistant.components.http import StaticPathConfig

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(card_path), False)]
        )
    except RuntimeError:
        # aiohttp refuses new routes once it has started: serve the card
        # after the next restart.
        _LOGGER.warning(
            "Could not register the dashboard card at %s, "
            "restart Home Assistant to serve it",
            CARD_URL,
        )