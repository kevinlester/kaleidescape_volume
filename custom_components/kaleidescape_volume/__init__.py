import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .pykaleidescape_fork.kaleidescape import Device as KaleidescapeDevice

from .bridge import (
    connect_device,
    connect_dispatcher,
    enable_volume_events_if_supported,
    disconnect_dispatcher,
    disconnect_device,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "kaleidescape_volume"

# Volume event constants
VOLUME_EVENT_TYPE = "USER_DEFINED_EVENT"
VOLUME_PREFIX = "VOLUME_"
VOLUME_SUFFIX = "_PRESS"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=10000): cv.port,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Kaleidescape volume sidecar."""
    conf = config.get(DOMAIN)
    if conf is None:
        _LOGGER.debug("No %s config found; not starting", DOMAIN)
        return True

    host = conf[CONF_HOST]
    port = conf[CONF_PORT]

    _LOGGER.info("Starting Kaleidescape volume bridge for %s:%s", host, port)

    device = KaleidescapeDevice(host, port=port)
    connection: Any | None = None

    def _handle_event(event: str) -> None:
        """Handle events from the Kaleidescape dispatcher."""
        text = str(event).strip()
        if not text:
            return

        _LOGGER.debug("Received Kaleidescape event: %r", text)

        parts = text.split(":", 1)
        if len(parts) != 2:
            return

        evt_type, name = (p.strip().upper() for p in parts)

        if evt_type != "USER_DEFINED_EVENT":
            return

        if not (name.startswith("VOLUME_") and name.endswith("_PRESS")):
            return

        _LOGGER.debug("Kaleidescape volume event: %s", name)

        hass.bus.fire(
            "kaleidescape_volume_button",
            {"event": name},
        )


    async def _async_stop(event: Any) -> None:
        """Handle Home Assistant stop to shut down the device cleanly."""
        _LOGGER.info("Stopping Kaleidescape volume bridge for %s:%s", host, port)
        nonlocal connection
        disconnect_dispatcher(connection)
        connection = None
        await disconnect_device(device)

    # Ensure we always clean up on shutdown
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_stop)

    # Connect device + dispatcher, then enable volume events
    if not await connect_device(device, host, port):
        # Don't crash HA startup; just skip the bridge
        return False

    connection = connect_dispatcher(device, _handle_event)
    await enable_volume_events_if_supported(device)

    return True
