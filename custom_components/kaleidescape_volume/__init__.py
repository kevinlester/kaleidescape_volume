import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .pykaleidescape_fork.kaleidescape import Device as KaleidescapeDevice

_LOGGER = logging.getLogger(__name__)

DOMAIN = "kaleidescape_volume"

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

    connection = None  # dispatcher connection, set after connect()

    def _handle_event(event: str) -> None:
        """
        Handle events from the Kaleidescape dispatcher.
        """
        name: str | None = None
        evt_type: str | None = None
        
        _LOGGER.debug("Received event[%s]: %s", type(event), event)
        
        text = str(event).strip()
        if not text:
            return

        parts = text.split(":", 1)
        if len(parts) != 2:
            return

        evt_type = parts[0].strip().upper()
        if evt_type != "USER_DEFINED_EVENT":
            return

        name = parts[1].strip().upper()
        if not name:
            return

        # Only care about volume button "PRESS" events
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

        # First, disconnect from the dispatcher (unsubscribe listener)
        nonlocal connection
        if connection is not None:
            try:
                disconnect = getattr(connection, "disconnect", None)
                if callable(disconnect):
                    disconnect()
                    _LOGGER.debug("Disconnected Kaleidescape dispatcher listener")
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    "Error while disconnecting Kaleidescape dispatcher listener"
                )
            finally:
                connection = None

        # Then, close the device connection
        try:
            if hasattr(device, "disconnect"):
                await device.disconnect()
            elif hasattr(device, "close"):
                await device.close()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Error while closing Kaleidescape device")

    # Register shutdown callback first so we always clean up
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_stop)

    # Now connect to the device and set up dispatcher listener
    try:
        await device.connect()
        _LOGGER.info("Connected to Kaleidescape at %s:%s", host, port)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Failed to connect to Kaleidescape device")
        # Don't crash HA startup; just skip the bridge
        return False

    dispatcher = getattr(device, "dispatcher", None)
    if dispatcher is not None and hasattr(dispatcher, "connect"):
        try:
            connection = dispatcher.connect(_handle_event)
            _LOGGER.debug("Connected Kaleidescape dispatcher listener")
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Failed to connect Kaleidescape dispatcher")
    else:
        _LOGGER.warning(
            "Kaleidescape device has no 'dispatcher'; "
            "volume button events will not be received."
        )
            
    # Enable the volume events if available on your fork
    if hasattr(device, "enable_volume_events"):
        try:
            await device.enable_volume_events()
            _LOGGER.info("Requested Kaleidescape volume events")
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Failed to enable volume events")
    else:
        _LOGGER.info(
            "not requesting volume events."
        )
    # No long-running task here; HA's loop stays alive, and pykaleidescape
    # manages its own internal tasks.
    return True
