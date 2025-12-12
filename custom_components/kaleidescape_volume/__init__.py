import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .pykaleidescape_fork.kaleidescape import Device as KaleidescapeDevice, const
from .volume_repeat import VolumeRepeatManager
from .bridge import (
    connect_device,
    connect_dispatcher,
    enable_volume_events_if_supported,
    disconnect_dispatcher,
    disconnect_device,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "kaleidescape_volume"


CONF_REPEAT_INTERVAL = "repeat_interval"
DEFAULT_REPEAT_INTERVAL = 0.25 # default seconds between repeated HA events

VOLUME_EVENTS = {
    "USER_DEFINED_EVENT:VOLUME_UP_PRESS",
    "USER_DEFINED_EVENT:VOLUME_UP_RELEASE",
    "USER_DEFINED_EVENT:VOLUME_DOWN_PRESS",
    "USER_DEFINED_EVENT:VOLUME_DOWN_RELEASE",
}

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=10000): cv.port,
                vol.Optional(
                    CONF_REPEAT_INTERVAL,
                    default=DEFAULT_REPEAT_INTERVAL,
                ): vol.All(
                    vol.Coerce(float),
                    vol.Range(min=0.05, max=2.0),
                ),
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
    repeat_interval = conf[CONF_REPEAT_INTERVAL]

    _LOGGER.info(
        "Starting Kaleidescape volume bridge for %s:%s (repeat_interval=%.3f)",
        host,
        port,
        repeat_interval,
    )
    
    device = KaleidescapeDevice(host, port=port)
    connection: Any | None = None
    repeat_mgr = VolumeRepeatManager(hass, repeat_interval)

    
    def _handle_event(event: str, params: list[str] = None) -> None:

        """Handle only the Kaleidescape volume button events."""
        if event != const.USER_DEFINED_EVENT:
            return
    
        name = params[0] # volume event name
        _LOGGER.debug("Kaleidescape volume event: %s", name)
    
        hass.bus.async_fire(
            "kaleidescape_volume_button",
            {"event": name},
        )

        # Start / stop repeating PRESS events
        if name == "VOLUME_UP_PRESS":
            repeat_mgr.start("VOLUME_UP_PRESS")
        elif name == "VOLUME_UP_RELEASE":
            repeat_mgr.stop("VOLUME_UP_PRESS")
        elif name == "VOLUME_DOWN_PRESS":
            repeat_mgr.start("VOLUME_DOWN_PRESS")
        elif name == "VOLUME_DOWN_RELEASE":
            repeat_mgr.stop("VOLUME_DOWN_PRESS")


    async def _async_stop(event: Any) -> None:
        """Handle Home Assistant stop to shut down the device cleanly."""
        _LOGGER.info("Stopping Kaleidescape volume bridge for %s:%s", host, port)
        nonlocal connection

        # Stop any ongoing repeat tasks
        repeat_mgr.stop_all()

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
